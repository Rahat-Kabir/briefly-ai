from __future__ import annotations

import asyncio
from pathlib import Path

import httpx
import pytest

from briefly_core.audio import (
    LOCAL_MEDIA_UPLOAD_LIMIT_BYTES,
    TranscriptionSegment,
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


def test_validate_local_media_rejects_oversized_file(tmp_path: Path) -> None:
    path = tmp_path / "large.mp3"
    with path.open("wb") as file:
        file.truncate(LOCAL_MEDIA_UPLOAD_LIMIT_BYTES + 1)

    with pytest.raises(ValueError, match="too large for direct Groq upload"):
        validate_local_media_file(path)


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
