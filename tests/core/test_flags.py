import pytest

from briefly_core.flags import (
    LengthArg,
    parse_brief_type,
    parse_extract_format,
    parse_length_arg,
    parse_max_extract_characters,
    parse_max_output_tokens,
    parse_stream_mode,
)


def test_parses_stream_mode() -> None:
    assert parse_stream_mode("auto") == "auto"
    assert parse_stream_mode("ON") == "on"
    assert parse_stream_mode("off") == "off"
    with pytest.raises(ValueError, match="Unsupported --stream"):
        parse_stream_mode("nope")


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
