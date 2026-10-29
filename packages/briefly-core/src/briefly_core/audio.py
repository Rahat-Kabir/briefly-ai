from __future__ import annotations

import asyncio
from dataclasses import dataclass
import os
from pathlib import Path
import tempfile
from typing import Any

import httpx

_DEFAULT_TIMEOUT_SECONDS = 60.0
DEFAULT_GROQ_TRANSCRIPTION_MODEL = "whisper-large-v3-turbo"
GROQ_TRANSCRIPTIONS_URL = "https://api.groq.com/openai/v1/audio/transcriptions"
LOCAL_MEDIA_UPLOAD_LIMIT_BYTES = 25 * 1024 * 1024

_AUDIO_EXTENSIONS = {
    ".flac",
    ".m4a",
    ".mp3",
    ".mpeg",
    ".mpga",
    ".ogg",
    ".wav",
}
_VIDEO_EXTENSIONS = {
    ".mp4",
    ".webm",
}
_SUPPORTED_MEDIA_EXTENSIONS = _AUDIO_EXTENSIONS | _VIDEO_EXTENSIONS


@dataclass(frozen=True)
class TranscriptionSegment:
    start_ms: int
    duration_ms: int
    text: str


@dataclass(frozen=True)
class TranscriptionResult:
    text: str
    segments: tuple[TranscriptionSegment, ...]
    model: str


def is_supported_audio_path(path: Path) -> bool:
    return path.suffix.lower() in _AUDIO_EXTENSIONS


def is_supported_video_path(path: Path) -> bool:
    return path.suffix.lower() in _VIDEO_EXTENSIONS


def is_supported_media_path(path: Path) -> bool:
    return path.suffix.lower() in _SUPPORTED_MEDIA_EXTENSIONS


def groq_transcription_model() -> str:
    return os.environ.get("BRIEFLY_GROQ_WHISPER_MODEL") or DEFAULT_GROQ_TRANSCRIPTION_MODEL


def validate_local_media_file(path: Path) -> None:
    if not path.exists() or not path.is_file():
        raise ValueError(f"Media file does not exist: {path}")
    if not is_supported_media_path(path):
        supported = ", ".join(sorted(_SUPPORTED_MEDIA_EXTENSIONS))
        raise ValueError(f"Unsupported local media file type: {path.suffix}. Supported: {supported}")


async def transcribe_local_media_file(path: Path) -> TranscriptionResult:
    validate_local_media_file(path)
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY is required to transcribe local media with Groq.")

    async with httpx.AsyncClient(timeout=_DEFAULT_TIMEOUT_SECONDS) as client:
        if path.stat().st_size <= LOCAL_MEDIA_UPLOAD_LIMIT_BYTES:
            return await transcribe_file_with_groq(path, api_key=api_key, client=client)

        with tempfile.TemporaryDirectory(prefix="briefly-media-") as temp_dir:
            compressed_path = await compress_media_for_transcription(path, Path(temp_dir))
            return await transcribe_file_with_groq(
                compressed_path,
                api_key=api_key,
                client=client,
            )


async def compress_media_for_transcription(path: Path, output_dir: Path) -> Path:
    """Re-encode to 32 kbps mono 16 kHz MP3, the format Whisper uses internally."""
    output_path = output_dir / f"{path.stem}.mp3"
    try:
        process = await asyncio.create_subprocess_exec(
            "ffmpeg",
            "-nostdin",
            "-v",
            "error",
            "-y",
            "-i",
            str(path),
            "-vn",
            "-ac",
            "1",
            "-ar",
            "16000",
            "-b:a",
            "32k",
            str(output_path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
    except FileNotFoundError as error:
        raise RuntimeError(
            "ffmpeg is required to shrink media over 25 MB before upload. Install ffmpeg."
        ) from error
    _, stderr = await process.communicate()
    if process.returncode != 0:
        error = stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"ffmpeg failed to compress {path.name}: {error or 'unknown error'}")
    return output_path


async def transcribe_file_with_groq(
    path: Path,
    *,
    api_key: str,
    client: httpx.AsyncClient,
    model: str | None = None,
) -> TranscriptionResult:
    size = path.stat().st_size
    if size > LOCAL_MEDIA_UPLOAD_LIMIT_BYTES:
        limit_mb = LOCAL_MEDIA_UPLOAD_LIMIT_BYTES // (1024 * 1024)
        raise RuntimeError(
            f"Audio is too large for Groq upload: {size / (1024 * 1024):.1f} MB "
            f"(limit {limit_mb} MB, about 1h45m of speech audio). Audio chunking is not "
            "implemented yet."
        )

    selected_model = model or groq_transcription_model()
    files = {
        "file": (
            path.name,
            path.read_bytes(),
            media_content_type(path),
        )
    }
    response = await client.post(
        GROQ_TRANSCRIPTIONS_URL,
        headers={"Authorization": f"Bearer {api_key}"},
        data={
            "model": selected_model,
            "response_format": "verbose_json",
            "temperature": "0",
        },
        files=files,
        timeout=_DEFAULT_TIMEOUT_SECONDS,
    )
    if response.status_code == 429:
        raise RuntimeError("Groq transcription rate limit or quota was reached.")
    if response.status_code != 200:
        raise RuntimeError(f"Groq transcription failed: HTTP {response.status_code}")

    try:
        payload = response.json()
    except ValueError as error:
        raise RuntimeError("Groq transcription returned invalid JSON.") from error
    if not isinstance(payload, dict):
        raise RuntimeError("Groq transcription returned an invalid response.")

    text = payload.get("text")
    if not isinstance(text, str) or not text.strip():
        raise RuntimeError("Groq transcription returned empty text.")

    cleaned_text = text.strip()
    segments = _groq_segments_to_transcription_segments(payload)
    if not segments:
        segments = (TranscriptionSegment(start_ms=0, duration_ms=0, text=cleaned_text),)

    return TranscriptionResult(text=cleaned_text, segments=segments, model=selected_model)


def media_content_type(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in {".mp3", ".mpeg", ".mpga"}:
        return "audio/mpeg"
    if suffix == ".m4a":
        return "audio/mp4"
    if suffix == ".mp4":
        return "video/mp4"
    if suffix == ".flac":
        return "audio/flac"
    if suffix == ".ogg":
        return "audio/ogg"
    if suffix == ".wav":
        return "audio/wav"
    if suffix == ".webm":
        return "video/webm"
    return "application/octet-stream"


def _groq_segments_to_transcription_segments(
    payload: dict[str, Any],
) -> tuple[TranscriptionSegment, ...]:
    raw_segments = payload.get("segments")
    if not isinstance(raw_segments, list):
        return ()

    segments: list[TranscriptionSegment] = []
    for segment in raw_segments:
        if not isinstance(segment, dict):
            continue
        text = segment.get("text")
        if not isinstance(text, str) or not text.strip():
            continue
        start_ms = _seconds_to_ms(segment.get("start"))
        end_ms = _seconds_to_ms(segment.get("end"))
        segments.append(
            TranscriptionSegment(
                start_ms=start_ms,
                duration_ms=max(0, end_ms - start_ms),
                text=text.strip(),
            )
        )
    return tuple(segments)


def _seconds_to_ms(raw: object) -> int:
    if not isinstance(raw, int | float) or isinstance(raw, bool):
        return 0
    return max(0, int(raw * 1000))
