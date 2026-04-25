# Testing

Use `uv` from the repo root.

On this Windows machine, use a workspace-local uv cache:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check
```

Current expected baseline:

```text
pytest: 45 passed
ruff: All checks passed
```

## Test Layout

```text
tests/
  cli/
    test_extract.py
    test_help.py
  core/
    test_briefing.py
    test_config.py
    test_flags.py
    test_input.py
    test_llm.py
```

## What Is Covered

- CLI help and version output.
- Root input command routing.
- Briefing request construction.
- Mocked LLM client behavior.
- Extract mode for literal text, local files, stdin, and URL placeholder errors.
- Placeholder briefing behavior.
- Flag parser behavior.
- Core input resolution.
- Config path resolution.
- Config JSON parsing.
- Config normalization and validation.

## What Is Not Covered Yet

- Live LLM calls.
- Content extraction.
- Cache behavior.
- Daemon routes.
- Slides/transcription behavior.
- Live network behavior.

Do not add live network tests to the default test suite.
