from __future__ import annotations

import asyncio

import click

from briefly_core.briefing import BriefingOptions, build_briefing_request
from briefly_core.flags import (
    parse_extract_format,
    parse_length_arg,
    parse_max_extract_characters,
    parse_max_output_tokens,
    parse_stream_mode,
)
from briefly_core.input import resolve_input_target
from briefly_core.llm import generate_brief


@click.command(hidden=True)
@click.argument("input", required=False)
@click.option("--extract-only", "--extract", is_flag=True, help="Extract content without briefing.")
@click.option("--output-format", "--format", default="text", help="Output format: text or markdown.")
@click.option("--length", default="medium", help="Brief length preset or character count.")
@click.option("--model", default=None, help="Model id or configured model preset.")
@click.option("--stream", default="auto", help="Streaming mode: auto, on, or off.")
@click.option(
    "--max-input-chars",
    "--max-extract-characters",
    default=None,
    help="Maximum extracted input characters, e.g. 50k.",
)
@click.option("--max-tokens", "--max-output-tokens", default=None, help="Maximum output tokens.")
@click.option("--skip-cache", "--no-cache", is_flag=True, help="Skip cache.")
def brief(
    input: str | None,
    extract_only: bool,
    output_format: str,
    length: str,
    model: str | None,
    stream: str,
    max_input_chars: str | None,
    max_tokens: str | None,
    skip_cache: bool,
) -> None:
    if input is None:
        raise click.UsageError("Missing input.")

    try:
        parsed_output_format = parse_extract_format(output_format)
        parsed_length = parse_length_arg(length)
        parse_stream_mode(stream)
        parsed_max_input_chars = parse_max_extract_characters(max_input_chars)
        parsed_max_tokens = parse_max_output_tokens(max_tokens)
    except ValueError as error:
        raise click.BadParameter(str(error)) from error

    resolved_input = resolve_input_target(
        input,
        stdin_reader=lambda: click.get_text_stream("stdin").read(),
    )

    if extract_only:
        if resolved_input.text is None:
            raise click.ClickException("URL extraction is not implemented yet.")
        click.echo(resolved_input.text, nl=not resolved_input.text.endswith("\n"))
        return

    try:
        briefing_options = BriefingOptions(
            length=parsed_length,
            output_format=parsed_output_format,
            model=model,
            max_input_chars=parsed_max_input_chars,
            max_output_tokens=parsed_max_tokens,
        )
        briefing_request = build_briefing_request(resolved_input, briefing_options)
    except ValueError as error:
        raise click.ClickException(str(error)) from error

    try:
        briefing_result = asyncio.run(generate_brief(briefing_request))
    except Exception as error:
        raise click.ClickException(str(error)) from error

    _ = skip_cache
    click.echo(briefing_result.text)
