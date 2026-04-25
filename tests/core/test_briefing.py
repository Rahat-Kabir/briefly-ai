import pytest

from briefly_core.briefing import BriefingOptions, build_briefing_request
from briefly_core.flags import LengthArg
from briefly_core.input import ResolvedInput


def test_builds_briefing_request_from_text() -> None:
    options = BriefingOptions(
        length=LengthArg(kind="preset", preset="short"),
        output_format="text",
        model="openai/gpt-5-mini",
        max_output_tokens=500,
    )

    request = build_briefing_request(
        ResolvedInput(kind="text", source="literal", text="Briefly builds requests."),
        options,
    )

    assert request.input_kind == "text"
    assert request.source == "literal"
    assert request.text == "Briefly builds requests."
    assert request.options == options
    assert "Create a short concise brief in plain text." in request.prompt
    assert "Briefly builds requests." in request.prompt


def test_applies_max_input_characters() -> None:
    request = build_briefing_request(
        ResolvedInput(kind="stdin", source="-", text="abcdefghij"),
        BriefingOptions(
            length=LengthArg(kind="preset", preset="medium"),
            output_format="text",
            max_input_chars=4,
        ),
    )

    assert request.text == "abcd"
    assert request.prompt.endswith("abcd")


def test_preserves_markdown_output_format() -> None:
    request = build_briefing_request(
        ResolvedInput(kind="file", source="notes.txt", text="Use markdown."),
        BriefingOptions(
            length=LengthArg(kind="chars", max_characters=1000),
            output_format="markdown",
        ),
    )

    assert request.options.output_format == "markdown"
    assert "Create a maximum 1000 character concise brief in Markdown." in request.prompt


def test_rejects_empty_text() -> None:
    with pytest.raises(ValueError, match="must not be empty"):
        build_briefing_request(
            ResolvedInput(kind="text", source="literal", text="   "),
            BriefingOptions(
                length=LengthArg(kind="preset", preset="medium"),
                output_format="text",
            ),
        )


def test_rejects_url_input_until_url_briefing_exists() -> None:
    with pytest.raises(ValueError, match="URL briefing is not implemented yet"):
        build_briefing_request(
            ResolvedInput(kind="url", source="https://example.com", text=None),
            BriefingOptions(
                length=LengthArg(kind="preset", preset="medium"),
                output_format="text",
            ),
        )
