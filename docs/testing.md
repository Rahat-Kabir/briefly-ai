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
pytest: 64 passed
ruff: All checks passed
```

## Test Layout

```text
tests/
  cli/
    test_extract.py
    test_help.py
    test_stream.py
  core/
    test_briefing.py
    test_content.py
    test_config.py
    test_flags.py
    test_input.py
    test_llm.py
```

## What Is Covered

- CLI help and version output.
- Root input command routing.
- Briefing request construction.
- Length preset and output-format prompt behavior.
- URL HTML extraction and URL briefing routing.
- Mocked LLM client behavior, including streaming chunks.
- CLI streaming on/off/auto paths and error reporting.
- Extract mode for literal text, local files, stdin, and URL placeholder errors.
- Placeholder briefing behavior.
- Flag parser behavior.
- Core input resolution.
- Config path resolution.
- Config JSON parsing.
- Config normalization and validation.

## What Is Not Covered Yet

- Live LLM calls.
- Non-HTML content extraction.
- Cache behavior.
- Daemon routes.
- Slides/transcription behavior.
- Live network behavior.

Do not add live network tests to the default test suite.
