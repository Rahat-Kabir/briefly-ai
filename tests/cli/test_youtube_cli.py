from __future__ import annotations

import json

from click.testing import CliRunner
import pytest

from briefly_cli.main import app
from briefly_core.youtube import CaptionSegment, YoutubeTranscript

runner = CliRunner()

_VIDEO_URL = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"


def _make_transcript() -> YoutubeTranscript:
    return YoutubeTranscript(
        video_id="dQw4w9WgXcQ",
        title="Demo Video",
        language_code="en",
        is_auto_generated=False,
        text="Hello world from a test. Later point.",
        segments=(
            CaptionSegment(start_ms=0, duration_ms=2000, text="Hello world from a test."),
            CaptionSegment(start_ms=61_000, duration_ms=2000, text="Later point."),
        ),
    )


def _patch_transcript(monkeypatch: pytest.MonkeyPatch, transcript: YoutubeTranscript) -> None:
    async def fake_fetch(url: str, **kwargs):
        assert url == _VIDEO_URL
        return transcript

    monkeypatch.setattr("briefly_cli.commands.brief.fetch_youtube_transcript", fake_fetch)


def test_extract_youtube_url(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_transcript(monkeypatch, _make_transcript())

    result = runner.invoke(app, [_VIDEO_URL, "--extract"], color=False)

    assert result.exit_code == 0, result.stdout
    assert result.stdout == "Demo Video\n\nHello world from a test. Later point.\n"


def test_extract_youtube_url_with_timestamps(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_transcript(monkeypatch, _make_transcript())

    result = runner.invoke(app, [_VIDEO_URL, "--extract", "--timestamps"], color=False)

    assert result.exit_code == 0, result.stdout
    assert result.stdout == "Demo Video\n\n[0:00] Hello world from a test.\n[1:01] Later point.\n"


def test_extract_youtube_url_json(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_transcript(monkeypatch, _make_transcript())

    result = runner.invoke(app, [_VIDEO_URL, "--extract", "--json"], color=False)

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["input"]["kind"] == "url"
    assert payload["input"]["source"] == _VIDEO_URL
    assert payload["extracted"]["kind"] == "url"
    assert payload["extracted"]["source"] == _VIDEO_URL
    assert "Demo Video" in payload["extracted"]["text"]
    assert "Hello world from a test. Later point." in payload["extracted"]["text"]
    assert payload["summary"] is None


def test_extract_youtube_url_json_with_timestamps(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_transcript(monkeypatch, _make_transcript())

    result = runner.invoke(app, [_VIDEO_URL, "--extract", "--json", "--timestamps"], color=False)

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert "[0:00] Hello world from a test." in payload["extracted"]["text"]
    assert "[1:01] Later point." in payload["extracted"]["text"]


def test_briefing_youtube_url(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_transcript(monkeypatch, _make_transcript())

    captured: dict[str, object] = {}

    async def fake_generate_brief(request):
        captured["text"] = request.text
        captured["model"] = request.options.model
        return type("Result", (), {"text": "BRIEFED", "model": request.options.model})()

    monkeypatch.setattr("briefly_cli.commands.brief.generate_brief", fake_generate_brief)

    result = runner.invoke(
        app,
        [_VIDEO_URL, "--model", "openai/gpt-5-mini", "--stream", "off"],
        color=False,
    )

    assert result.exit_code == 0, result.stdout
    assert result.stdout.strip() == "BRIEFED"
    assert "Hello world from a test." in str(captured["text"])
    assert captured["model"] == "openai/gpt-5-mini"


def test_youtube_no_captions_error(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_fetch(url: str, **kwargs):
        raise ValueError("No captions available for this video: dQw4w9WgXcQ")

    monkeypatch.setattr("briefly_cli.commands.brief.fetch_youtube_transcript", fake_fetch)

    result = runner.invoke(app, [_VIDEO_URL, "--extract"], color=False)

    assert result.exit_code != 0
    assert "No captions available" in result.stderr


def test_youtube_url_uses_separate_cache_slot(monkeypatch: pytest.MonkeyPatch) -> None:
    transcript = _make_transcript()
    fetch_calls = {"count": 0}

    async def fake_fetch(url: str, **kwargs):
        fetch_calls["count"] += 1
        return transcript

    monkeypatch.setattr("briefly_cli.commands.brief.fetch_youtube_transcript", fake_fetch)

    first = runner.invoke(app, [_VIDEO_URL, "--extract"], color=False)
    assert first.exit_code == 0, first.stdout
    second = runner.invoke(app, [_VIDEO_URL, "--extract"], color=False)
    assert second.exit_code == 0, second.stdout

    assert fetch_calls["count"] == 1
    assert first.stdout == second.stdout


def test_youtube_timestamps_use_separate_cache_slot(monkeypatch: pytest.MonkeyPatch) -> None:
    transcript = _make_transcript()
    fetch_calls = {"count": 0}

    async def fake_fetch(url: str, **kwargs):
        fetch_calls["count"] += 1
        return transcript

    monkeypatch.setattr("briefly_cli.commands.brief.fetch_youtube_transcript", fake_fetch)

    plain = runner.invoke(app, [_VIDEO_URL, "--extract"], color=False)
    assert plain.exit_code == 0, plain.stdout
    timestamped = runner.invoke(app, [_VIDEO_URL, "--extract", "--timestamps"], color=False)
    assert timestamped.exit_code == 0, timestamped.stdout
    timestamped_again = runner.invoke(app, [_VIDEO_URL, "--extract", "--timestamps"], color=False)
    assert timestamped_again.exit_code == 0, timestamped_again.stdout

    assert fetch_calls["count"] == 2
    assert "[0:00]" not in plain.stdout
    assert "[0:00]" in timestamped.stdout
    assert timestamped.stdout == timestamped_again.stdout
