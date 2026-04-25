from __future__ import annotations

from dataclasses import dataclass

from briefly_core.flags import ExtractFormat, LengthArg
from briefly_core.input import InputKind, ResolvedInput


@dataclass(frozen=True)
class BriefingOptions:
    length: LengthArg
    output_format: ExtractFormat
    model: str | None = None
    max_input_chars: int | None = None
    max_output_tokens: int | None = None


@dataclass(frozen=True)
class BriefingRequest:
    input_kind: InputKind
    source: str
    text: str
    prompt: str
    options: BriefingOptions


def build_briefing_request(
    resolved_input: ResolvedInput,
    options: BriefingOptions,
) -> BriefingRequest:
    if resolved_input.kind == "url":
        raise ValueError("URL briefing is not implemented yet.")

    if resolved_input.text is None:
        raise ValueError("Input did not resolve to text.")

    text = resolved_input.text.strip()
    if not text:
        raise ValueError("Input text must not be empty.")

    if options.max_input_chars is not None:
        text = text[: options.max_input_chars]

    return BriefingRequest(
        input_kind=resolved_input.kind,
        source=resolved_input.source,
        text=text,
        prompt=_build_prompt(text, options),
        options=options,
    )


def _build_prompt(text: str, options: BriefingOptions) -> str:
    length = _length_label(options.length)
    format_label = "Markdown" if options.output_format == "markdown" else "plain text"
    return (
        f"Create a {length} concise brief in {format_label}.\n\n"
        "Focus on the main ideas, useful details, and any important caveats.\n\n"
        f"Input:\n{text}"
    )


def _length_label(length: LengthArg) -> str:
    if length.kind == "chars":
        return f"maximum {length.max_characters} character"
    if length.preset is None:
        raise ValueError("Length preset is missing.")
    return length.preset
