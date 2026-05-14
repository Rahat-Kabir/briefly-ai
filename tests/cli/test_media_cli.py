from __future__ import annotations

import json
import os
from pathlib import Path

from click.testing import CliRunner
import pytest

from briefly_cli.main import app
from briefly_core.audio import LOCAL_MEDIA_UPLOAD_LIMIT_BYTES, TranscriptionResult

runner = CliRunner()


def _write_media(directory: Path, name: str = "meeting.mp3", content: bytes = b"audio") -> Path:
    path = directory / name
    path.write_bytes(content)
    return path


def _patch_transcription(monkeypatch: pytest.MonkeyPatch, text: str = "Meeting transcript.") -> None:
    async def fake_transcribe(path: Path):
        assert path.exists()
        return TranscriptionResult(text=text, segments=(), model="whisper-large-v3-turbo")

    monkeypatch.setattr("briefly_cli.commands.brief.transcribe_local_media_file", fake_transcribe)


def test_extract_local_audio(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    media_path = _write_media(tmp_path)
    _patch_transcription(monkeypatch)

    result = runner.invoke(app, [str(media_path), "--extract"], color=False)

    assert result.exit_code == 0, result.stdout
    assert result.stdout == "Meeting transcript.\n"


def test_extract_local_video(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    media_path = _write_media(tmp_path, name="lecture.mp4", content=b"video")
    _patch_transcription(monkeypatch, text="Lecture transcript.")

    result = runner.invoke(app, [str(media_path), "--extract"], color=False)

    assert result.exit_code == 0, result.stdout
    assert result.stdout == "Lecture transcript.\n"


def test_extract_local_audio_json(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    media_path = _write_media(tmp_path)
    _patch_transcription(monkeypatch)

    result = runner.invoke(app, [str(media_path), "--extract", "--json"], color=False)

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["input"]["kind"] == "audio"
    assert payload["input"]["source"] == str(media_path)
    assert payload["extracted"] == {
        "kind": "audio",
        "source": str(media_path),
        "text": "Meeting transcript.",
    }
    assert payload["summary"] is None


def test_briefing_local_audio(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    media_path = _write_media(tmp_path)
    _patch_transcription(monkeypatch, text="Briefing input from audio")

    captured: dict[str, object] = {}

    async def fake_generate_brief(request):
        captured["text"] = request.text
        captured["kind"] = request.input_kind
        captured["model"] = request.options.model
        return type("Result", (), {"text": "BRIEFED", "model": request.options.model})()

    monkeypatch.setattr("briefly_cli.commands.brief.generate_brief", fake_generate_brief)

    result = runner.invoke(
        app,
        [str(media_path), "--model", "openai/gpt-5-mini", "--stream", "off"],
        color=False,
    )

    assert result.exit_code == 0, result.stdout
    assert result.stdout.strip() == "BRIEFED"
    assert captured["text"] == "Briefing input from audio"
    assert captured["kind"] == "audio"
    assert captured["model"] == "openai/gpt-5-mini"


def test_media_transcription_uses_cache(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    media_path = _write_media(tmp_path)
    calls = {"count": 0}

    async def fake_transcribe(path: Path):
        calls["count"] += 1
        return TranscriptionResult(text="Cached transcript.", segments=(), model="whisper-large-v3-turbo")

    monkeypatch.setattr("briefly_cli.commands.brief.transcribe_local_media_file", fake_transcribe)

    first = runner.invoke(app, [str(media_path), "--extract"], color=False)
    assert first.exit_code == 0, first.stdout
    second = runner.invoke(app, [str(media_path), "--extract"], color=False)
    assert second.exit_code == 0, second.stdout

    assert calls["count"] == 1
    assert first.stdout == second.stdout


def test_media_cache_invalidated_on_mtime_change(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    media_path = _write_media(tmp_path)
    calls = {"count": 0}

    async def fake_transcribe(path: Path):
        calls["count"] += 1
        return TranscriptionResult(
            text=f"Transcript {calls['count']}.",
            segments=(),
            model="whisper-large-v3-turbo",
        )

    monkeypatch.setattr("briefly_cli.commands.brief.transcribe_local_media_file", fake_transcribe)

    first = runner.invoke(app, [str(media_path), "--extract"], color=False)
    assert first.exit_code == 0, first.stdout

    media_path.write_bytes(b"updated-audio")
    new_time = media_path.stat().st_mtime + 5
    os.utime(media_path, (new_time, new_time))

    second = runner.invoke(app, [str(media_path), "--extract"], color=False)
    assert second.exit_code == 0, second.stdout

    assert calls["count"] == 2
    assert "Transcript 2." in second.stdout


def test_media_skip_cache_retranscribes(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    media_path = _write_media(tmp_path)
    calls = {"count": 0}

    async def fake_transcribe(path: Path):
        calls["count"] += 1
        return TranscriptionResult(text="Repeat transcript.", segments=(), model="whisper-large-v3-turbo")

    monkeypatch.setattr("briefly_cli.commands.brief.transcribe_local_media_file", fake_transcribe)

    first = runner.invoke(app, [str(media_path), "--extract", "--skip-cache"], color=False)
    assert first.exit_code == 0, first.stdout
    second = runner.invoke(app, [str(media_path), "--extract", "--skip-cache"], color=False)
    assert second.exit_code == 0, second.stdout

    assert calls["count"] == 2


def test_local_media_missing_groq_key_errors(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    media_path = _write_media(tmp_path)

    result = runner.invoke(app, [str(media_path), "--extract"], color=False)

    assert result.exit_code != 0
    assert "GROQ_API_KEY is required" in result.stderr


def test_local_media_oversized_file_errors(tmp_path: Path) -> None:
    media_path = tmp_path / "large.mp3"
    with media_path.open("wb") as file:
        file.truncate(LOCAL_MEDIA_UPLOAD_LIMIT_BYTES + 1)

    result = runner.invoke(app, [str(media_path), "--extract"], color=False)

    assert result.exit_code != 0
    assert "too large for direct Groq upload" in result.stderr
