from __future__ import annotations

import asyncio

import click

from briefly_core.briefing import BriefingOptions, build_briefing_request
from briefly_core.cache import (
    get_summary_cache,
    get_url_cache,
    set_summary_cache,
    set_url_cache,
)
from briefly_core.config import ConfigData, load_config
from briefly_core.content import ExtractedContent, extract_url
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

    try:
        config = load_config().config if not extract_only or not skip_cache else None
    except Exception as error:
        raise click.ClickException(str(error)) from error

    if extract_only:
        try:
            extracted_input = asyncio.run(
                _resolve_extractable_input(
                    resolved_input,
                    output_format=parsed_output_format,
                    skip_cache=skip_cache,
                    cache_ttl_days=_cache_ttl_days(config),
                )
            )
        except Exception as error:
            raise click.ClickException(str(error)) from error
        extracted_text = extracted_input.text or ""
        click.echo(extracted_text, nl=not extracted_text.endswith("\n"))
        return

    try:
        resolved_briefing_input = asyncio.run(
            _resolve_extractable_input(
                resolved_input,
                output_format=parsed_output_format,
                skip_cache=skip_cache,
                cache_ttl_days=_cache_ttl_days(config),
            )
        )
        resolved_model = _resolve_model(model, config)
        briefing_options = BriefingOptions(
            length=parsed_length,
            output_format=parsed_output_format,
            model=resolved_model,
            max_input_chars=parsed_max_input_chars,
            max_output_tokens=parsed_max_tokens,
        )
        briefing_request = build_briefing_request(resolved_briefing_input, briefing_options)
    except Exception as error:
        raise click.ClickException(str(error)) from error

    if not skip_cache:
        cached_summary = _get_summary_cache(briefing_request, _cache_ttl_days(config))
        if cached_summary is not None:
            click.echo(cached_summary.text)
            return

    if _should_stream(parsed_stream_mode):
        try:
            streamed_text = asyncio.run(_run_stream(briefing_request))
            if not skip_cache:
                set_summary_cache(briefing_request, streamed_text)
        except Exception as error:
            raise click.ClickException(str(error)) from error
        return

    try:
        briefing_result = asyncio.run(generate_brief(briefing_request))
    except Exception as error:
        raise click.ClickException(str(error)) from error

    if not skip_cache:
        set_summary_cache(briefing_request, briefing_result.text)

    click.echo(briefing_result.text)


def _should_stream(mode: StreamMode) -> bool:
    if mode == "on":
        return True
    if mode == "off":
        return False
    return click.get_text_stream("stdout").isatty()


def _cache_ttl_days(config: ConfigData | None) -> float | None:
    cache = config.get("cache") if config else None
    if not isinstance(cache, dict):
        return None

    ttl_days = cache.get("ttlDays")
    if isinstance(ttl_days, int | float) and not isinstance(ttl_days, bool):
        return float(ttl_days)
    return None


def _get_summary_cache(request, cache_ttl_days: float | None):
    if cache_ttl_days is None:
        return get_summary_cache(request)
    return get_summary_cache(request, ttl_days=cache_ttl_days)


def _get_url_cache(requested_url: str, output_format: str, cache_ttl_days: float | None):
    if cache_ttl_days is None:
        return get_url_cache(requested_url, output_format=output_format)
    return get_url_cache(requested_url, output_format=output_format, ttl_days=cache_ttl_days)


def _resolve_model(model: str | None, config: ConfigData | None) -> str | None:
    if model is not None:
        model_value = model.strip()
        if "/" in model_value:
            return model_value
        return _resolve_named_model(model_value, config)

    if config is None:
        return None

    configured_model = config.get("model")
    if configured_model is None:
        return None

    return _resolve_config_model(configured_model, config)


def _resolve_named_model(name: str, config: ConfigData | None) -> str:
    models = config.get("models") if config else None
    if not isinstance(models, dict) or name not in models:
        raise ValueError(f"Unknown model preset: {name}")
    return _resolve_config_model(models[name], config)


def _resolve_config_model(model: object, config: ConfigData) -> str | None:
    if not isinstance(model, dict):
        raise ValueError("Configured model must be an object.")

    model_id = model.get("id")
    if isinstance(model_id, str):
        return model_id

    model_name = model.get("name")
    if isinstance(model_name, str):
        return _resolve_named_model(model_name, config)

    return None


async def _run_stream(request) -> str:
    stdout = click.get_text_stream("stdout")
    last_char = ""
    chunks: list[str] = []
    async for chunk in generate_brief_stream(request):
        stdout.write(chunk)
        stdout.flush()
        chunks.append(chunk)
        if chunk:
            last_char = chunk[-1]
    if last_char and last_char != "\n":
        stdout.write("\n")
        stdout.flush()
    return "".join(chunks).strip()


async def _resolve_extractable_input(
    resolved_input: ResolvedInput,
    *,
    output_format: str = "text",
    skip_cache: bool = False,
    cache_ttl_days: float | None = None,
) -> ResolvedInput:
    if resolved_input.kind == "url":
        if not skip_cache:
            cached_url = _get_url_cache(resolved_input.source, output_format, cache_ttl_days)
            if cached_url is not None:
                return _resolved_url_input(cached_url)

        extracted = await extract_url(resolved_input.source, output_format=output_format)
        if not skip_cache:
            set_url_cache(resolved_input.source, extracted, output_format=output_format)
        return _resolved_url_input(extracted)

    if resolved_input.text is None:
        raise ValueError("Input did not resolve to text.")
    return resolved_input


def _resolved_url_input(extracted: ExtractedContent) -> ResolvedInput:
    if extracted.title:
        text = f"{extracted.title}\n\n{extracted.text}"
    else:
        text = extracted.text
    return ResolvedInput(kind="url", source=extracted.source, text=text)
