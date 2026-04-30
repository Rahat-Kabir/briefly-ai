import pytest

from briefly_core.flags import (
    LengthArg,
    parse_brief_type,
    parse_duration_ms,
    parse_extract_format,
    parse_firecrawl_mode,
    parse_length_arg,
    parse_markdown_mode,
    parse_max_extract_characters,
    parse_max_output_tokens,
    parse_metrics_mode,
    parse_preprocess_mode,
    parse_retries,
    parse_stream_mode,
    parse_video_mode,
    parse_youtube_mode,
)


def test_parses_youtube_mode() -> None:
    assert parse_youtube_mode("auto") == "auto"
    assert parse_youtube_mode("web") == "web"
    assert parse_youtube_mode("apify") == "apify"
    assert parse_youtube_mode("yt-dlp") == "yt-dlp"
    assert parse_youtube_mode("no-auto") == "no-auto"
    assert parse_youtube_mode("autp") == "auto"
    with pytest.raises(ValueError, match="Unsupported --youtube"):
        parse_youtube_mode("nope")


def test_parses_timeout_durations() -> None:
    assert parse_duration_ms("30") == 30_000
    assert parse_duration_ms("30s") == 30_000
    assert parse_duration_ms("2m") == 120_000
    assert parse_duration_ms("500ms") == 500
    assert parse_duration_ms("1.5s") == 1500
    with pytest.raises(ValueError, match="Unsupported --timeout"):
        parse_duration_ms("0")


def test_parses_modes() -> None:
    assert parse_firecrawl_mode("always") == "always"
    assert parse_markdown_mode("readability") == "readability"
    assert parse_preprocess_mode("on") == "always"
    assert parse_stream_mode("auto") == "auto"
    assert parse_metrics_mode("detailed") == "detailed"
    assert parse_video_mode("understand") == "understand"


def test_parses_extract_format() -> None:
    assert parse_extract_format("md") == "markdown"
    assert parse_extract_format("markdown") == "markdown"
    assert parse_extract_format("text") == "text"
    assert parse_extract_format("plain") == "text"
    with pytest.raises(ValueError, match="Unsupported --format"):
        parse_extract_format("nope")


def test_parses_brief_type() -> None:
    assert parse_brief_type("standard") == "standard"
    assert parse_brief_type("EXECUTIVE") == "executive"
    assert parse_brief_type("action") == "action"
    assert parse_brief_type("study") == "study"
    assert parse_brief_type("decision") == "decision"
    with pytest.raises(ValueError, match="Unsupported --brief-type"):
        parse_brief_type("technical")


def test_parses_length_as_preset_or_character_count() -> None:
    assert parse_length_arg("medium") == LengthArg(kind="preset", preset="medium")
    assert parse_length_arg("s") == LengthArg(kind="preset", preset="short")
    assert parse_length_arg("20k") == LengthArg(kind="chars", max_characters=20_000)
    assert parse_length_arg("1500") == LengthArg(kind="chars", max_characters=1500)
    assert parse_length_arg("10") == LengthArg(kind="chars", max_characters=10)
    with pytest.raises(ValueError, match="Unsupported --length"):
        parse_length_arg("9")
    with pytest.raises(ValueError, match="Unsupported --length"):
        parse_length_arg("nope")


def test_parses_max_output_tokens() -> None:
    assert parse_max_output_tokens(None) is None
    assert parse_max_output_tokens("2k") == 2000
    assert parse_max_output_tokens("1500") == 1500
    assert parse_max_output_tokens("16") == 16
    with pytest.raises(ValueError, match="Unsupported --max-output-tokens"):
        parse_max_output_tokens("15")
    with pytest.raises(ValueError, match="Unsupported --max-output-tokens"):
        parse_max_output_tokens("nope")


def test_parses_max_extract_characters() -> None:
    assert parse_max_extract_characters(None) is None
    assert parse_max_extract_characters("0") is None
    assert parse_max_extract_characters("8k") == 8000
    assert parse_max_extract_characters("15000") == 15000
    with pytest.raises(ValueError, match="max-extract-characters"):
        parse_max_extract_characters("5")
    with pytest.raises(ValueError, match="max-extract-characters"):
        parse_max_extract_characters("nope")


def test_parses_retries() -> None:
    assert parse_retries("0") == 0
    assert parse_retries("5") == 5
    with pytest.raises(ValueError, match="Unsupported --retries"):
        parse_retries("6")
    with pytest.raises(ValueError, match="Unsupported --retries"):
        parse_retries("1.5")
