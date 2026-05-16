# Testing

Use `uv` from the repo root.

Default commands:

```powershell
uv run pytest
uv run ruff check
```

On some Windows setups, uv's default cache or hardlink behavior may fail with
permission errors. If that happens, set these once in the shell:

```powershell
$env:UV_CACHE_DIR='.uv-cache'
$env:UV_LINK_MODE='copy'
```

Current expected baseline:

```text
pytest: 211 passed
ruff: All checks passed
```

## Test Layout

```text
tests/
  cli/
    conftest.py
    test_cache_cli.py
    test_cache_commands.py
    test_config_init.py
    test_config_model.py
    test_extract.py
    test_help.py
    test_image_cli.py
    test_json_output.py
    test_media_cli.py
    test_pdf_cli.py
    test_short_input_hint.py
    test_stream.py
    test_youtube_cli.py
  core/
    test_audio.py
    test_briefing.py
    test_cache.py
    test_content.py
    test_config.py
    test_flags.py
    test_image.py
    test_input.py
    test_llm.py
    test_pdf.py
    test_youtube.py
```

## What Is Covered

- CLI help and version output.
- Root input command routing.
- Briefing request construction.
- Brief type, length preset, and output-format prompt behavior.
- Short-input hint behavior, including stderr output and suppression in
  `--extract`, `--json`, and long-form length paths.
- URL HTML extraction, Markdown mode, trafilatura fallback behavior, and URL
  briefing routing.
- YouTube captions, transcript formatting, timestamps, JSON output, and cache
  separation.
- Groq Whisper YouTube fallback with mocked audio download and API response.
- Local audio/video transcription with mocked Groq responses, including cache
  hit, mtime invalidation, skip-cache, missing key, and oversized file errors.
- Local image extraction with a mocked vision LLM, including extension
  detection, content-type mapping, vision-message shape, error wrapping,
  empty-response handling, extract/brief flows, JSON output, cache hit,
  mtime invalidation, skip-cache, `--vision-model` override, and config
  `vision.model` / fallback resolution.
- PDF text extraction via pdfplumber, metadata title fallback, multi-page
  joining, empty-PDF error, and CLI cache hit / mtime invalidation /
  `--skip-cache` paths.
- Remote PDF URL extraction by content type or `.pdf` URL path.
- Scanned-PDF fallback to a vision LLM: 50-char threshold detector,
  fallback triggers, text PDFs skip it, missing-vision-model error, and
  cache invalidation on vision-model change.
- Mocked LLM client behavior, including streaming chunks.
- CLI streaming on/off/auto paths and error reporting.
- CLI assertions use Click's split `result.stdout` and `result.stderr` streams
  where output channel matters.
- Structured JSON output for extract mode, briefing mode, cache hits, and
  stream-disabled JSON mode, including `briefType`.
- Config-backed model resolution and `config init`.
- URL and summary cache behavior, TTL, stats, and clear.
- Summary cache separation by brief type.
- Extract mode for literal text, local files, stdin, and URL placeholder errors.
- Placeholder briefing behavior.
- Flag parser behavior.
- Core input resolution.
- Config path resolution.
- Config JSON parsing.
- Config normalization and validation.

## What Is Not Covered Yet

- Live LLM calls.
- Live Groq transcription calls.
- Live YouTube/network behavior.
- Non-HTML content extraction.
- Daemon routes.
- Slides/transcription behavior.

Do not add live network tests to the default test suite.
