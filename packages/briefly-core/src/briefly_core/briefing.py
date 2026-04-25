from __future__ import annotations

from dataclasses import dataclass, replace

from briefly_core.flags import BriefLength, ExtractFormat, LengthArg
from briefly_core.input import InputKind, ResolvedInput

_PRESET_MAX_OUTPUT_TOKENS: dict[BriefLength, int] = {
    "short": 120,
    "medium": 300,
    "long": 700,
    "xl": 1200,
    "xxl": 2000,
}

_PRESET_INSTRUCTIONS: dict[BriefLength, tuple[str, ...]] = {
    "short": (
        "Write a short brief.",
        "Use 2-3 sentences.",
        "Do not use headings or bullets.",
    ),
    "medium": (
        "Write a medium brief.",
        "Use one short paragraph followed by 3 concise bullets.",
    ),
    "long": (
        "Write a structured brief.",
        "Use short sections and bullets where useful.",
    ),
    "xl": (
        "Write a detailed brief.",
        "Cover the main ideas, useful details, and important caveats.",
    ),
    "xxl": (
        "Write a comprehensive brief.",
        "Cover context, main ideas, details, caveats, and practical takeaways.",
    ),
}


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
    if resolved_input.kind == "url" and resolved_input.text is None:
        raise ValueError("URL briefing is not implemented yet.")

    if resolved_input.text is None:
        raise ValueError("Input did not resolve to text.")

    text = resolved_input.text.strip()
    if not text:
        raise ValueError("Input text must not be empty.")

    if options.max_input_chars is not None:
        text = text[: options.max_input_chars]

    resolved_options = _resolve_options(options)
    return BriefingRequest(
        input_kind=resolved_input.kind,
        source=resolved_input.source,
        text=text,
        prompt=_build_prompt(text, resolved_options),
        options=resolved_options,
    )


def _build_prompt(text: str, options: BriefingOptions) -> str:
    instructions = [*_length_instructions(options.length), *_format_instructions(options.output_format)]
    instruction_text = "\n".join(f"- {instruction}" for instruction in instructions)
    return (
        "Create a concise brief from the input.\n\n"
        f"Instructions:\n{instruction_text}\n"
        "- Focus on the main ideas, useful details, and important caveats.\n"
        "- Do not pad with unnecessary background.\n\n"
        f"Input:\n{text}"
    )


def _resolve_options(options: BriefingOptions) -> BriefingOptions:
    if options.max_output_tokens is not None:
        return options
    if options.length.kind != "preset":
        return options
    if options.length.preset is None:
        raise ValueError("Length preset is missing.")
    return replace(options, max_output_tokens=_PRESET_MAX_OUTPUT_TOKENS[options.length.preset])


def _length_instructions(length: LengthArg) -> tuple[str, ...]:
    if length.kind == "chars":
        return (f"Write a brief no longer than {length.max_characters} characters.",)
    if length.preset is None:
        raise ValueError("Length preset is missing.")
    return _PRESET_INSTRUCTIONS[length.preset]


def _format_instructions(output_format: ExtractFormat) -> tuple[str, ...]:
    if output_format == "markdown":
        return ("Markdown output is allowed.",)
    return ("Use plain text only.", "Do not use Markdown formatting.")
