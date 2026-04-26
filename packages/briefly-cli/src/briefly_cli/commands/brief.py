from __future__ import annotations

import asyncio

import click

from briefly_core.briefing import BriefingOptions, build_briefing_request
from briefly_core.content import extract_url
from briefly_core.flags import (
    StreamMode,
    parse_extract_format,
    parse_length_arg,
    parse_max_extract_characters,
    parse_max_output_tokens,
    parse_stream_mode,
)
from briefly_core.input import ResolvedInput, resolve_input_target
from briefly_core.llm import generate_brief, generate_brief_stream


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
        parsed_stream_mode = parse_stream_mode(stream)
        parsed_max_input_chars = parse_max_extract_characters(max_input_chars)
        parsed_max_tokens = parse_max_output_tokens(max_tokens)
    except ValueError as error:
        raise click.BadParameter(str(error)) from error

    resolved_input = resolve_input_target(
        input,
        stdin_reader=lambda: click.get_text_stream("stdin").read(),
    )

    if extract_only:
        try:
            extracted_input = asyncio.run(_resolve_extractable_input(resolved_input))
        except Exception as error:
            raise click.ClickException(str(error)) from error
        extracted_text = extracted_input.text or ""
        click.echo(extracted_text, nl=not extracted_text.endswith("\n"))
        return

    try:
        resolved_briefing_input = asyncio.run(_resolve_extractable_input(resolved_input))
        briefing_options = BriefingOptions(
            length=parsed_length,
            output_format=parsed_output_format,
            model=model,
            max_input_chars=parsed_max_input_chars,
            max_output_tokens=parsed_max_tokens,
        )
        briefing_request = build_briefing_request(resolved_briefing_input, briefing_options)
    except Exception as error:
        raise click.ClickException(str(error)) from error

    _ = skip_cache

    if _should_stream(parsed_stream_mode):
        try:
            asyncio.run(_run_stream(briefing_request))
        except Exception as error:
            raise click.ClickException(str(error)) from error
        return

    try:
        briefing_result = asyncio.run(generate_brief(briefing_request))
    except Exception as error:
        raise click.ClickException(str(error)) from error

    click.echo(briefing_result.text)


def _should_stream(mode: StreamMode) -> bool:
    if mode == "on":
        return True
    if mode == "off":
        return False
    return click.get_text_stream("stdout").isatty()


async def _run_stream(request) -> None:
    stdout = click.get_text_stream("stdout")
    last_char = ""
    async for chunk in generate_brief_stream(request):
        stdout.write(chunk)
        stdout.flush()
        if chunk:
            last_char = chunk[-1]
    if last_char and last_char != "\n":
        stdout.write("\n")
        stdout.flush()


async def _resolve_extractable_input(resolved_input: ResolvedInput) -> ResolvedInput:
    if resolved_input.kind == "url":
        extracted = await extract_url(resolved_input.source)
        source = extracted.source
        if extracted.title:
            text = f"{extracted.title}\n\n{extracted.text}"
        else:
            text = extracted.text
        return ResolvedInput(kind="url", source=source, text=text)

    if resolved_input.text is None:
        raise ValueError("Input did not resolve to text.")
    return resolved_input
