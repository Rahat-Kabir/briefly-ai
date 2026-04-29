from __future__ import annotations

import asyncio
import json

import httpx
import pytest

from briefly_core.youtube import (
    CaptionSegment,
    YoutubeTranscript,
    extract_initial_player_response,
    extract_innertube_api_key,
    fetch_youtube_transcript,
    is_youtube_url,
    parse_caption_xml,
    parse_video_id,
    pick_caption_track,
    transcript_to_text,
)
from briefly_core.youtube import _normalize_caption_url


def test_is_youtube_url_accepts_known_hosts() -> None:
    assert is_youtube_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    assert is_youtube_url("https://youtu.be/dQw4w9WgXcQ")
    assert is_youtube_url("https://m.youtube.com/watch?v=dQw4w9WgXcQ")
    assert is_youtube_url("https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ")


def test_is_youtube_url_rejects_others() -> None:
    assert not is_youtube_url("https://example.com/watch?v=dQw4w9WgXcQ")
    assert not is_youtube_url("ftp://www.youtube.com/watch?v=dQw4w9WgXcQ")
    assert not is_youtube_url("not a url")


def test_parse_video_id_handles_url_shapes() -> None:
    assert parse_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ") == "dQw4w9WgXcQ"
    assert parse_video_id("https://youtu.be/dQw4w9WgXcQ") == "dQw4w9WgXcQ"
    assert parse_video_id("https://www.youtube.com/shorts/dQw4w9WgXcQ") == "dQw4w9WgXcQ"
    assert parse_video_id("https://www.youtube.com/embed/dQw4w9WgXcQ") == "dQw4w9WgXcQ"
    assert parse_video_id("https://www.youtube.com/live/dQw4w9WgXcQ") == "dQw4w9WgXcQ"
    assert (
        parse_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ&list=PL1234")
        == "dQw4w9WgXcQ"
    )


def test_parse_video_id_rejects_invalid_inputs() -> None:
    assert parse_video_id("https://example.com/watch?v=dQw4w9WgXcQ") is None
    assert parse_video_id("https://www.youtube.com/watch") is None
    assert parse_video_id("https://www.youtube.com/watch?v=tooshort") is None
    assert parse_video_id("https://www.youtube.com/feed/trending") is None


def test_extract_innertube_api_key_finds_value() -> None:
    html = 'noise "INNERTUBE_API_KEY":"AIzaSyABC123" trailing'
    assert extract_innertube_api_key(html) == "AIzaSyABC123"


def test_extract_innertube_api_key_missing_returns_none() -> None:
    assert extract_innertube_api_key("nothing here") is None


def test_extract_initial_player_response_parses_object() -> None:
    payload = {"videoDetails": {"title": "Demo Video"}, "captions": {}}
    serialized = json.dumps(payload)
    html = f'<script>var ytInitialPlayerResponse = {serialized};</script>'
    parsed = extract_initial_player_response(html)

    assert parsed is not None
    assert parsed["videoDetails"]["title"] == "Demo Video"


def test_extract_initial_player_response_handles_nested_braces() -> None:
    payload = {
        "videoDetails": {"title": "Has } brace and \" quote", "lengthSeconds": "42"},
        "captions": {"playerCaptionsTracklistRenderer": {"captionTracks": []}},
    }
    serialized = json.dumps(payload)
    html = f"prefix ytInitialPlayerResponse = {serialized}, more"
    parsed = extract_initial_player_response(html)

    assert parsed is not None
    assert parsed["videoDetails"]["title"] == 'Has } brace and " quote'


def test_extract_initial_player_response_missing_returns_none() -> None:
    assert extract_initial_player_response("<html></html>") is None


def test_pick_caption_track_prefers_manual_english_first() -> None:
    player_response = {
        "captions": {
            "playerCaptionsTracklistRenderer": {
                "captionTracks": [
                    {"languageCode": "fr", "baseUrl": "fr-url"},
                    {"languageCode": "en", "baseUrl": "en-url"},
                ],
                "automaticCaptions": [
                    {"languageCode": "en", "kind": "asr", "baseUrl": "en-asr-url"},
                ],
            }
        }
    }
    track = pick_caption_track(player_response)
    assert track is not None
    assert track["baseUrl"] == "en-url"


def test_pick_caption_track_falls_back_to_asr_when_no_manual() -> None:
    player_response = {
        "playerCaptionsTracklistRenderer": {
            "automaticCaptions": [
                {"languageCode": "en", "kind": "asr", "baseUrl": "en-asr-url"},
            ]
        }
    }
    track = pick_caption_track(player_response)
    assert track is not None
    assert track["baseUrl"] == "en-asr-url"


def test_pick_caption_track_skip_auto_generated() -> None:
    player_response = {
        "playerCaptionsTracklistRenderer": {
            "captionTracks": [],
            "automaticCaptions": [
                {"languageCode": "en", "kind": "asr", "baseUrl": "en-asr-url"},
            ],
        }
    }
    assert pick_caption_track(player_response, skip_auto_generated=True) is None


def test_pick_caption_track_dedupes_by_language() -> None:
    player_response = {
        "playerCaptionsTracklistRenderer": {
            "captionTracks": [
                {"languageCode": "en", "baseUrl": "first-en"},
                {"languageCode": "en", "baseUrl": "second-en"},
            ]
        }
    }
    track = pick_caption_track(player_response)
    assert track is not None
    assert track["baseUrl"] == "first-en"


def test_pick_caption_track_returns_none_when_no_tracks() -> None:
    assert pick_caption_track({}) is None
    assert pick_caption_track({"captions": {}}) is None


def test_parse_caption_xml_decodes_entities_and_segments() -> None:
    xml = (
        '<?xml version="1.0" encoding="utf-8"?>'
        '<transcript>'
        '<text start="0.5" dur="2">Hello &amp; welcome</text>'
        '<text start="2.5" dur="1.5">It&#39;s &lt;great&gt;</text>'
        '<text start="4" dur="1"></text>'
        '</transcript>'
    )
    segments = parse_caption_xml(xml)
    assert segments == (
        CaptionSegment(start_ms=500, duration_ms=2000, text="Hello & welcome"),
        CaptionSegment(start_ms=2500, duration_ms=1500, text="It's <great>"),
    )


def test_parse_caption_xml_decodes_double_encoded_entities() -> None:
    xml = (
        '<transcript>'
        '<text start="0" dur="1">It&amp;#39;s &amp;gt; here</text>'
        '</transcript>'
    )
    segments = parse_caption_xml(xml)
    assert segments == (CaptionSegment(start_ms=0, duration_ms=1000, text="It's > here"),)


def test_parse_caption_xml_handles_empty_input() -> None:
    assert parse_caption_xml("") == ()
    assert parse_caption_xml("<transcript></transcript>") == ()


def test_normalize_caption_url_strips_fmt_param() -> None:
    assert (
        _normalize_caption_url("https://example.com/api?lang=en&fmt=srv3&kind=asr")
        == "https://example.com/api?lang=en&kind=asr"
    )
    assert (
        _normalize_caption_url("https://example.com/api?fmt=srv3&lang=en")
        == "https://example.com/api?lang=en"
    )
    assert (
        _normalize_caption_url("https://example.com/api?lang=en&fmt=srv3")
        == "https://example.com/api?lang=en"
    )
    assert (
        _normalize_caption_url("https://example.com/api?lang=en")
        == "https://example.com/api?lang=en"
    )


def test_parse_caption_xml_strips_inline_tags() -> None:
    xml = '<transcript><text start="0" dur="1">a <b>bold</b> word</text></transcript>'
    segments = parse_caption_xml(xml)
    assert segments == (CaptionSegment(start_ms=0, duration_ms=1000, text="a bold word"),)


def test_transcript_to_text_can_include_timestamps() -> None:
    transcript = YoutubeTranscript(
        video_id="dQw4w9WgXcQ",
        title="Demo Video",
        language_code="en",
        is_auto_generated=False,
        text="Intro Deep point Later point",
        segments=(
            CaptionSegment(start_ms=0, duration_ms=1200, text="Intro"),
            CaptionSegment(start_ms=61_000, duration_ms=1000, text="Deep point"),
            CaptionSegment(start_ms=3_661_000, duration_ms=1000, text="Later point"),
        ),
    )

    assert transcript_to_text(transcript) == "Intro Deep point Later point"
    assert transcript_to_text(transcript, timestamps=True) == (
        "[0:00] Intro\n[1:01] Deep point\n[1:01:01] Later point"
    )


def _make_client(handler) -> httpx.AsyncClient:
    transport = httpx.MockTransport(handler)
    return httpx.AsyncClient(transport=transport)


def test_fetch_youtube_transcript_uses_android_player_first() -> None:
    android_player_response = {
        "videoDetails": {"title": "Demo Video"},
        "captions": {
            "playerCaptionsTracklistRenderer": {
                "captionTracks": [
                    {
                        "languageCode": "en",
                        "baseUrl": "https://www.youtube.com/api/timedtext?lang=en",
                    }
                ]
            }
        },
    }
    caption_xml = (
        '<transcript>'
        '<text start="0" dur="2">Hello world</text>'
        '<text start="2" dur="2">From a test</text>'
        '</transcript>'
    )
    seen_paths: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen_paths.append(request.url.path)
        if request.url.path == "/youtubei/v1/player":
            assert request.method == "POST"
            body = json.loads(request.content.decode("utf-8"))
            assert body["context"]["client"]["clientName"] == "ANDROID"
            assert body["videoId"] == "dQw4w9WgXcQ"
            return httpx.Response(200, json=android_player_response)
        if request.url.path == "/api/timedtext":
            return httpx.Response(200, text=caption_xml)
        raise AssertionError(f"Unexpected request: {request.url}")

    async def run() -> None:
        async with _make_client(handler) as client:
            transcript = await fetch_youtube_transcript(
                "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                client=client,
            )
        assert transcript.video_id == "dQw4w9WgXcQ"
        assert transcript.title == "Demo Video"
        assert transcript.language_code == "en"
        assert transcript.is_auto_generated is False
        assert transcript.text == "Hello world From a test"
        assert len(transcript.segments) == 2
        assert "/watch" not in seen_paths

    asyncio.run(run())


def test_fetch_youtube_transcript_falls_back_to_watch_page_for_fresh_key() -> None:
    fallback_response = {
        "videoDetails": {"title": "Fallback Title"},
        "captions": {
            "playerCaptionsTracklistRenderer": {
                "captionTracks": [
                    {
                        "languageCode": "en",
                        "kind": "asr",
                        "baseUrl": "https://www.youtube.com/api/timedtext?from=fallback",
                    }
                ]
            }
        },
    }
    watch_html = '<script>"INNERTUBE_API_KEY":"AIzaSyROTATED"</script>'
    caption_xml = '<transcript><text start="0" dur="1">Fallback caption</text></transcript>'
    seen_keys: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/watch":
            return httpx.Response(200, text=watch_html)
        if request.url.path == "/youtubei/v1/player":
            seen_keys.append(request.url.params.get("key") or "")
            if request.url.params.get("key") == "AIzaSyROTATED":
                return httpx.Response(200, json=fallback_response)
            return httpx.Response(200, json={})
        if request.url.path == "/api/timedtext":
            return httpx.Response(200, text=caption_xml)
        raise AssertionError(f"Unexpected request: {request.url}")

    async def run() -> None:
        async with _make_client(handler) as client:
            transcript = await fetch_youtube_transcript(
                "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                client=client,
            )
        assert transcript.title == "Fallback Title"
        assert transcript.is_auto_generated is True
        assert transcript.text == "Fallback caption"
        assert seen_keys[0] != "AIzaSyROTATED"
        assert "AIzaSyROTATED" in seen_keys

    asyncio.run(run())


def test_fetch_youtube_transcript_errors_when_no_captions() -> None:
    no_captions_response = {
        "videoDetails": {"title": "No captions"},
        "captions": {"playerCaptionsTracklistRenderer": {"captionTracks": []}},
    }
    watch_html = '<script>"INNERTUBE_API_KEY":"AIzaSyROTATED"</script>'

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/watch":
            return httpx.Response(200, text=watch_html)
        if request.url.path == "/youtubei/v1/player":
            return httpx.Response(200, json=no_captions_response)
        raise AssertionError(f"Unexpected request: {request.url}")

    async def run() -> None:
        async with _make_client(handler) as client:
            with pytest.raises(ValueError, match="No captions available"):
                await fetch_youtube_transcript(
                    "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                    client=client,
                )

    asyncio.run(run())


def test_fetch_youtube_transcript_rejects_invalid_url() -> None:
    async def run() -> None:
        with pytest.raises(ValueError, match="Unsupported YouTube URL"):
            await fetch_youtube_transcript("https://www.youtube.com/feed/trending")

    asyncio.run(run())


def test_fetch_youtube_transcript_errors_when_all_paths_fail() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/youtubei/v1/player":
            return httpx.Response(503, text="boom")
        if request.url.path == "/watch":
            return httpx.Response(429, text="rate limited")
        raise AssertionError(f"Unexpected request: {request.url}")

    async def run() -> None:
        async with _make_client(handler) as client:
            with pytest.raises(ValueError, match="No captions available"):
                await fetch_youtube_transcript(
                    "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                    client=client,
                )

    asyncio.run(run())
