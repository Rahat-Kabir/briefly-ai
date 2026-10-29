from __future__ import annotations

import asyncio
from pathlib import Path

import httpx
import pytest

from briefly_core.audio import (
    LOCAL_MEDIA_UPLOAD_LIMIT_BYTES,
    TranscriptionResult,
    TranscriptionSegment,
    compress_media_for_transcription,
    is_supported_audio_path,
    is_supported_media_path,
    is_supported_video_path,
    media_content_type,
    transcribe_file_with_groq,
    transcribe_local_media_file,
    validate_local_media_file,
)


def test_media_extension_detection() -> None:
    assert is_supported_audio_path(Path("meeting.mp3"))
    assert is_supported_audio_path(Path("meeting.wav"))
    assert is_supported_video_path(Path("lecture.mp4"))
    assert is_supported_video_path(Path("lecture.webm"))
    assert is_supported_media_path(Path("meeting.m4a"))
    assert not is_supported_media_path(Path("notes.txt"))


def test_media_content_type() -> None:
    assert media_content_type(Path("meeting.mp3")) == "audio/mpeg"
    assert media_content_type(Path("meeting.m4a")) == "audio/mp4"
    assert media_content_type(Path("lecture.mp4")) == "video/mp4"
    assert media_content_type(Path("lecture.webm")) == "video/webm"
    assert media_content_type(Path("meeting.flac")) == "audio/flac"


def test_validate_local_media_rejects_unsupported_file(tmp_path: Path) -> None:
    path = tmp_path / "clip.aac"
    path.write_bytes(b"audio")

    with pytest.raises(ValueError, match="Unsupported local media file type"):
        validate_local_media_file(path)


def _patch_groq_upload(monkeypatch: pytest.MonkeyPatch) -> list[Path]:
    uploaded: list[Path] = []

    async def fake_transcribe(path: Path, **kwargs: object) -> TranscriptionResult:
        uploaded.append(path)
        return TranscriptionResult(text="Transcript.", segments=(), model="whisper")

    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    monkeypatch.setattr("briefly_core.audio.transcribe_file_with_groq", fake_transcribe)
    return uploaded


def test_transcribe_local_media_uploads_small_file_without_compressing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    uploaded = _patch_groq_upload(monkeypatch)

    async def fail_compress(path: Path, output_dir: Path) -> Path:
        raise AssertionError("Small media must not be compressed.")

    monkeypatch.setattr("briefly_core.audio.compress_media_for_transcription", fail_compress)
    path = tmp_path / "meeting.mp3"
    path.write_bytes(b"audio")

    asyncio.run(transcribe_local_media_file(path))

    assert uploaded == [path]


def test_transcribe_local_media_compresses_large_file_before_upload(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    uploaded = _patch_groq_upload(monkeypatch)

    async def fake_compress(path: Path, output_dir: Path) -> Path:
        compressed_path = output_dir / "lecture.mp3"
        compressed_path.write_bytes(b"small")
        return compressed_path

    monkeypatch.setattr("briefly_core.audio.compress_media_for_transcription", fake_compress)
    path = tmp_path / "lecture.mp4"
    with path.open("wb") as file:
        file.truncate(LOCAL_MEDIA_UPLOAD_LIMIT_BYTES + 1)

    asyncio.run(transcribe_local_media_file(path))

    assert len(uploaded) == 1
    assert uploaded[0].name == "lecture.mp3"
    assert uploaded[0].parent != tmp_path
    assert not uploaded[0].exists()


def test_compress_media_runs_ffmpeg_for_mono_speech_mp3(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    captured: list[tuple[str, ...]] = []

    class FakeProcess:
        returncode = 0

        async def communicate(self) -> tuple[bytes, bytes]:
            return b"", b""

    async def fake_exec(*args: str, **kwargs: object) -> FakeProcess:
        captured.append(args)
        return FakeProcess()

    monkeypatch.setattr("briefly_core.audio.asyncio.create_subprocess_exec", fake_exec)
    source = tmp_path / "lecture.mp4"

    output = asyncio.run(compress_media_for_transcription(source, tmp_path / "out"))

    assert output == tmp_path / "out" / "lecture.mp3"
    args = captured[0]
    assert args[0] == "ffmpeg"
    assert args[args.index("-i") + 1] == str(source)
    assert "-vn" in args
    assert args[args.index("-ac") + 1] == "1"
    assert args[args.index("-ar") + 1] == "16000"
    assert args[args.index("-b:a") + 1] == "32k"
    assert args[-1] == str(output)


def test_compress_media_reports_missing_ffmpeg(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    async def missing_exec(*args: str, **kwargs: object) -> None:
        raise FileNotFoundError("ffmpeg")

    monkeypatch.setattr("briefly_core.audio.asyncio.create_subprocess_exec", missing_exec)

    with pytest.raises(RuntimeError, match="ffmpeg is required"):
        asyncio.run(compress_media_for_transcription(tmp_path / "a.mp3", tmp_path))


def test_compress_media_reports_ffmpeg_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    class FakeProcess:
        returncode = 1

        async def communicate(self) -> tuple[bytes, bytes]:
            return b"", b"Invalid data found when processing input"

    async def fake_exec(*args: str, **kwargs: object) -> FakeProcess:
        return FakeProcess()

    monkeypatch.setattr("briefly_core.audio.asyncio.create_subprocess_exec", fake_exec)

    with pytest.raises(RuntimeError, match="ffmpeg failed to compress a.mp3: Invalid data"):
        asyncio.run(compress_media_for_transcription(tmp_path / "a.mp3", tmp_path))


def test_transcribe_local_media_requires_groq_api_key(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    path = tmp_path / "meeting.mp3"
    path.write_bytes(b"audio")

    async def run() -> None:
        with pytest.raises(RuntimeError, match="GROQ_API_KEY is required"):
            await transcribe_local_media_file(path)

    asyncio.run(run())


def test_transcribe_file_with_groq_posts_audio_and_parses_segments(tmp_path: Path) -> None:
    path = tmp_path / "meeting.mp3"
    path.write_bytes(b"audio-bytes")

    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == "https://api.groq.com/openai/v1/audio/transcriptions"
        assert request.headers["Authorization"] == "Bearer test-key"
        assert b'name="model"\r\n\r\nwhisper-large-v3-turbo' in request.content
        assert b"audio-bytes" in request.content
        return httpx.Response(
            200,
            json={
                "text": " Groq transcript. ",
                "segments": [{"start": 0.25, "end": 1.75, "text": " Groq transcript. "}],
            },
        )

    async def run() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            result = await transcribe_file_with_groq(path, api_key="test-key", client=client)
        assert result.text == "Groq transcript."
        assert result.model == "whisper-large-v3-turbo"
        assert result.segments == (
            TranscriptionSegment(start_ms=250, duration_ms=1500, text="Groq transcript."),
        )

    asyncio.run(run())


def test_transcribe_file_with_groq_reports_rate_limit(tmp_path: Path) -> None:
    path = tmp_path / "meeting.mp3"
    path.write_bytes(b"audio-bytes")

    async def run() -> None:
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(lambda request: httpx.Response(429))
        ) as client:
            with pytest.raises(RuntimeError, match="rate limit or quota"):
                await transcribe_file_with_groq(path, api_key="test-key", client=client)

    asyncio.run(run())


def test_transcribe_file_with_groq_rejects_oversized_file_before_upload(tmp_path: Path) -> None:
    path = tmp_path / "large.mp3"
    with path.open("wb") as file:
        file.truncate(LOCAL_MEDIA_UPLOAD_LIMIT_BYTES + 1)

    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError("Oversized audio must not be uploaded.")

    async def run() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            with pytest.raises(RuntimeError, match="too large for Groq upload"):
                await transcribe_file_with_groq(path, api_key="test-key", client=client)

    asyncio.run(run())


def test_transcribe_file_with_groq_overrides_short_client_timeout(tmp_path: Path) -> None:
    path = tmp_path / "meeting.mp3"
    path.write_bytes(b"audio-bytes")

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.extensions["timeout"]["read"] == 60.0
        return httpx.Response(200, json={"text": "Groq transcript."})

    async def run() -> None:
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler),
            timeout=15.0,
        ) as client:
            result = await transcribe_file_with_groq(path, api_key="test-key", client=client)
        assert result.text == "Groq transcript."

    asyncio.run(run())
