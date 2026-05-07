from __future__ import annotations

import asyncio
import json
from pathlib import Path

import click

from briefly_core.audio import groq_transcription_model, transcribe_local_media_file
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
    parse_brief_type,
    parse_extract_format,
    parse_length_arg,
    parse_max_extract_characters,
    parse_max_output_tokens,
    parse_stream_mode,
)
from briefly_core.input import ResolvedInput, resolve_input_target
from briefly_core.llm import generate_brief, generate_brief_stream
from briefly_core.pdf import extract_pdf
from briefly_core.youtube import (
    fetch_youtube_transcript,
    is_youtube_url,
    transcript_to_extracted_content,
)

_YOUTUBE_CACHE_KIND = "youtube_transcript"
_YOUTUBE_CACHE_FORMAT = "text"
_PDF_CACHE_KIND = "pdf_extract"
_MEDIA_CACHE_KIND = "media_transcript"


@click.command(hidden=True)
@click.argument("input", required=False)
@click.option("--extract-only", "--extract", is_flag=True, help="Extract content without briefing.")
@click.option("--output-format", "--format", default="text", help="Output format: text or markdown.")
@click.option(
    "--brief-type",
    default="standard",
    help="Brief type: standard, executive, action, study, or decision.",
)
@click.option("--length", default="medium", help="Brief length preset or character count.")
@click.option("--model", default=None, help="Model id or configured model preset.")
@click.option("--stream", default="auto", help="Streaming mode: auto, on, or off.")
@click.option("--json", "json_output", is_flag=True, help="Output structured JSON.")
@click.option("--timestamps", is_flag=True, help="Include transcript timestamps when available.")
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
    brief_type: str,
    length: str,
    model: str | None,
    stream: str,
    json_output: bool,
    timestamps: bool,
    max_input_chars: str | None,
    max_tokens: str | None,
    skip_cache: bool,
) -> None:
    if input is None:
        raise click.UsageError("Missing input.")

    try:
        parsed_output_format = parse_extract_format(output_format)
        parsed_brief_type = parse_brief_type(brief_type)
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
                    timestamps=timestamps,
                )
            )
        except Exception as error:
            raise click.ClickException(str(error)) from error
        if json_output:
            _echo_json(
                {
                    "input": _input_payload(
                        resolved_input,
                        output_format=parsed_output_format,
                        brief_type=parsed_brief_type,
                        length=parsed_length,
                        max_input_chars=parsed_max_input_chars,
                        max_output_tokens=parsed_max_tokens,
                        model=None,
                    ),
                    "extracted": _resolved_input_payload(extracted_input),
                    "prompt": None,
                    "llm": None,
                    "cache": {"enabled": not skip_cache},
                    "summary": None,
                }
            )
            return
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
                timestamps=timestamps,
            )
        )
        resolved_model = _resolve_model(model, config)
        briefing_options = BriefingOptions(
            length=parsed_length,
            output_format=parsed_output_format,
            brief_type=parsed_brief_type,
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
            if json_output:
                _echo_json(
                    _briefing_payload(
                        resolved_input=resolved_input,
                        extracted_input=resolved_briefing_input,
                        briefing_request=briefing_request,
                        summary=cached_summary.text,
                        model=briefing_request.options.model,
                        cache_enabled=True,
                        summary_cache_hit=True,
                    )
                )
                return
            click.echo(cached_summary.text)
            return

    if not json_output and _should_stream(parsed_stream_mode):
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

    if json_output:
        _echo_json(
            _briefing_payload(
                resolved_input=resolved_input,
                extracted_input=resolved_briefing_input,
                briefing_request=briefing_request,
                summary=briefing_result.text,
                model=getattr(briefing_result, "model", briefing_request.options.model),
                cache_enabled=not skip_cache,
                summary_cache_hit=False,
            )
        )
        return

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


def _get_url_cache(
    requested_url: str,
    output_format: str,
    cache_ttl_days: float | None,
    *,
    cache_kind: str = "url_extract",
):
    if cache_ttl_days is None:
        return get_url_cache(
            requested_url,
            output_format=output_format,
            cache_kind=cache_kind,
        )
    return get_url_cache(
        requested_url,
        output_format=output_format,
        ttl_days=cache_ttl_days,
        cache_kind=cache_kind,
    )


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
    timestamps: bool = False,
) -> ResolvedInput:
    if resolved_input.kind == "url":
        if is_youtube_url(resolved_input.source):
            return await _resolve_youtube_input(
                resolved_input.source,
                skip_cache=skip_cache,
                cache_ttl_days=cache_ttl_days,
                timestamps=timestamps,
            )

        if not skip_cache:
            cached_url = _get_url_cache(resolved_input.source, output_format, cache_ttl_days)
            if cached_url is not None:
                return _resolved_url_input(cached_url)

        extracted = await extract_url(resolved_input.source, output_format=output_format)
        if not skip_cache:
            set_url_cache(resolved_input.source, extracted, output_format=output_format)
        return _resolved_url_input(extracted)

    if resolved_input.kind == "pdf":
        return await _resolve_pdf_input(
            Path(resolved_input.source),
            skip_cache=skip_cache,
            cache_ttl_days=cache_ttl_days,
        )

    if resolved_input.kind in {"audio", "video"}:
        return await _resolve_media_input(
            resolved_input,
            skip_cache=skip_cache,
            cache_ttl_days=cache_ttl_days,
        )

    if resolved_input.text is None:
        raise ValueError("Input did not resolve to text.")
    return resolved_input


async def _resolve_pdf_input(
    path: Path,
    *,
    skip_cache: bool,
    cache_ttl_days: float | None,
) -> ResolvedInput:
    cache_format = _pdf_cache_format(path)
    if not skip_cache:
        cached = _get_url_cache(
            str(path),
            cache_format,
            cache_ttl_days,
            cache_kind=_PDF_CACHE_KIND,
        )
        if cached is not None:
            return _resolved_pdf_input(cached)

    extracted = await asyncio.to_thread(extract_pdf, path)
    if not skip_cache:
        set_url_cache(
            str(path),
            extracted,
            output_format=cache_format,
            cache_kind=_PDF_CACHE_KIND,
        )
    return _resolved_pdf_input(extracted)


def _pdf_cache_format(path: Path) -> str:
    return f"text:{path.stat().st_mtime_ns}"


def _resolved_pdf_input(extracted: ExtractedContent) -> ResolvedInput:
    if extracted.title:
        text = f"{extracted.title}\n\n{extracted.text}"
    else:
        text = extracted.text
    return ResolvedInput(kind="pdf", source=extracted.source, text=text)


async def _resolve_media_input(
    resolved_input: ResolvedInput,
    *,
    skip_cache: bool,
    cache_ttl_days: float | None,
) -> ResolvedInput:
    path = Path(resolved_input.source)
    cache_format = _media_cache_format(path)
    if not skip_cache:
        cached = _get_url_cache(
            str(path),
            cache_format,
            cache_ttl_days,
            cache_kind=_MEDIA_CACHE_KIND,
        )
        if cached is not None:
            return _resolved_media_input(cached, kind=resolved_input.kind)

    transcription = await transcribe_local_media_file(path)
    extracted = ExtractedContent(source=str(path), title=None, text=transcription.text)
    if not skip_cache:
        set_url_cache(
            str(path),
            extracted,
            output_format=cache_format,
            cache_kind=_MEDIA_CACHE_KIND,
        )
    return _resolved_media_input(extracted, kind=resolved_input.kind)


def _media_cache_format(path: Path) -> str:
    stat = path.stat()
    return f"text:{stat.st_mtime_ns}:{stat.st_size}:{groq_transcription_model()}"


def _resolved_media_input(extracted: ExtractedContent, *, kind: str) -> ResolvedInput:
    return ResolvedInput(kind=kind, source=extracted.source, text=extracted.text)


async def _resolve_youtube_input(
    url: str,
    *,
    skip_cache: bool,
    cache_ttl_days: float | None,
    timestamps: bool,
) -> ResolvedInput:
    output_format = _youtube_cache_format(timestamps)
    if not skip_cache:
        cached = _get_url_cache(
            url,
            output_format,
            cache_ttl_days,
            cache_kind=_YOUTUBE_CACHE_KIND,
        )
        if cached is not None:
            return _resolved_url_input(cached)

    transcript = await fetch_youtube_transcript(url)
    extracted = transcript_to_extracted_content(
        transcript,
        source_url=url,
        timestamps=timestamps,
    )
    if not skip_cache:
        set_url_cache(
            url,
            extracted,
            output_format=output_format,
            cache_kind=_YOUTUBE_CACHE_KIND,
        )
    return _resolved_url_input(extracted)


def _youtube_cache_format(timestamps: bool) -> str:
    return "text-timestamps" if timestamps else _YOUTUBE_CACHE_FORMAT


def _resolved_url_input(extracted: ExtractedContent) -> ResolvedInput:
    if extracted.title:
        text = f"{extracted.title}\n\n{extracted.text}"
    else:
        text = extracted.text
    return ResolvedInput(kind="url", source=extracted.source, text=text)


def _briefing_payload(
    *,
    resolved_input: ResolvedInput,
    extracted_input: ResolvedInput,
    briefing_request,
    summary: str,
    model: str | None,
    cache_enabled: bool,
    summary_cache_hit: bool,
) -> dict[str, object]:
    return {
        "input": _input_payload(
            resolved_input,
            output_format=briefing_request.options.output_format,
            brief_type=briefing_request.options.brief_type,
            length=briefing_request.options.length,
            max_input_chars=briefing_request.options.max_input_chars,
            max_output_tokens=briefing_request.options.max_output_tokens,
            model=briefing_request.options.model,
        ),
        "extracted": _resolved_input_payload(extracted_input),
        "prompt": briefing_request.prompt,
        "llm": {"model": model},
        "cache": {
            "enabled": cache_enabled,
            "summaryHit": summary_cache_hit,
        },
        "summary": summary,
    }


def _input_payload(
    resolved_input: ResolvedInput,
    *,
    output_format: str,
    brief_type: str,
    length,
    max_input_chars: int | None,
    max_output_tokens: int | None,
    model: str | None,
) -> dict[str, object]:
    return {
        "kind": resolved_input.kind,
        "source": resolved_input.source,
        "format": output_format,
        "briefType": brief_type,
        "length": _length_payload(length),
        "maxInputChars": max_input_chars,
        "maxOutputTokens": max_output_tokens,
        "model": model,
    }


def _length_payload(length) -> dict[str, object]:
    if length.kind == "preset":
        return {"kind": "preset", "preset": length.preset}
    return {"kind": "chars", "maxCharacters": length.max_characters}


def _resolved_input_payload(resolved_input: ResolvedInput) -> dict[str, object]:
    return {
        "kind": resolved_input.kind,
        "source": resolved_input.source,
        "text": resolved_input.text,
    }


def _echo_json(payload: dict[str, object]) -> None:
    click.echo(json.dumps(payload, indent=2, ensure_ascii=False))
