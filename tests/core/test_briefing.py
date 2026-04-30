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
    assert "- Write a short brief." in request.prompt
    assert "- Use 2-3 sentences." in request.prompt
    assert "- Do not use headings or bullets." in request.prompt
    assert "- Do not use Markdown formatting." in request.prompt
    assert "Briefly builds requests." in request.prompt


def test_adds_brief_type_instructions() -> None:
    cases = {
        "executive": "Frame the brief for a business or leadership reader.",
        "action": "Do not invent owners, deadlines, or commitments",
        "study": "Make the brief useful for learning and retention.",
        "decision": "If evidence is missing, say what information is needed.",
    }

    for brief_type, expected_instruction in cases.items():
        request = build_briefing_request(
            ResolvedInput(kind="text", source="literal", text="Brief this."),
            BriefingOptions(
                length=LengthArg(kind="preset", preset="medium"),
                output_format="text",
                brief_type=brief_type,
            ),
        )

        assert request.options.brief_type == brief_type
        assert expected_instruction in request.prompt


def test_standard_brief_type_keeps_general_prompt() -> None:
    request = build_briefing_request(
        ResolvedInput(kind="text", source="literal", text="Brief this."),
        BriefingOptions(
            length=LengthArg(kind="preset", preset="medium"),
            output_format="text",
        ),
    )

    assert request.options.brief_type == "standard"
    assert "Frame the brief for a business or leadership reader." not in request.prompt


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
    assert request.options.max_output_tokens == 300


def test_preserves_markdown_output_format() -> None:
    request = build_briefing_request(
        ResolvedInput(kind="file", source="notes.txt", text="Use markdown."),
        BriefingOptions(
            length=LengthArg(kind="chars", max_characters=1000),
            output_format="markdown",
        ),
    )

    assert request.options.output_format == "markdown"
    assert "- Write a brief no longer than 1000 characters." in request.prompt
    assert "- Markdown output is allowed." in request.prompt


def test_adds_default_token_cap_for_length_preset() -> None:
    request = build_briefing_request(
        ResolvedInput(kind="text", source="literal", text="Keep it short."),
        BriefingOptions(
            length=LengthArg(kind="preset", preset="short"),
            output_format="text",
        ),
    )

    assert request.options.max_output_tokens == 120


def test_explicit_max_tokens_overrides_length_default() -> None:
    request = build_briefing_request(
        ResolvedInput(kind="text", source="literal", text="Keep it short."),
        BriefingOptions(
            length=LengthArg(kind="preset", preset="short"),
            output_format="text",
            max_output_tokens=80,
        ),
    )

    assert request.options.max_output_tokens == 80


def test_long_prompt_allows_structure() -> None:
    request = build_briefing_request(
        ResolvedInput(kind="text", source="literal", text="A longer topic."),
        BriefingOptions(
            length=LengthArg(kind="preset", preset="long"),
            output_format="markdown",
        ),
    )

    assert "- Write a structured brief." in request.prompt
    assert "- Use short sections and bullets where useful." in request.prompt
    assert request.options.max_output_tokens == 700


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


def test_builds_briefing_request_from_extracted_url_text() -> None:
    request = build_briefing_request(
        ResolvedInput(
            kind="url",
            source="https://example.com/final",
            text="Example Domain\n\nThis domain is for examples.",
        ),
        BriefingOptions(
            length=LengthArg(kind="preset", preset="short"),
            output_format="text",
        ),
    )

    assert request.input_kind == "url"
    assert request.source == "https://example.com/final"
    assert request.text == "Example Domain\n\nThis domain is for examples."
