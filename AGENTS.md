# Briefly AI - Agent Guide

Briefly AI is an individual Python product for creating concise briefs from
text, files, URLs, and later richer sources such as media and slides.

## Core Principles

- **Think Before Coding**: State assumptions. If uncertain, ask. Don't guess.
- **Simplicity First**: No overengineering. No "flexibility" that wasn't asked for.
- **Surgical Changes**: Only touch what is necessary. Don't reformat adjacent code.
- **Goal-Driven**: Create verifiable success criteria, then make them pass.

## Code Quality

- **Fail Fast**: Do not swallow exceptions. Prefer a clear failure over silent
behavior. Only catch errors with a specific recovery plan.
- **Senior Engineer Test**: Before writing, ask: "Would a senior engineer
delete this?" If yes, simplify.
- **Clean Up Orphans**: If you remove a function or variable, remove its unused
imports, tests, and dependencies too.

## Global

- `AGENTS.md` is the source of truth. `CLAUDE.md` must stay byte-identical.
Any edit to `AGENTS.md` must be mirrored to `CLAUDE.md` in the same change.
- After adding a new file, tool, or feature, update `README.md` and the Project
Structure section in this file to reflect the change.
- After code changes, update `docs/tech_spec.md` and `docs/progress.md` with
the decisions made in the session. Update `docs/testing.md` when test
workflow or coverage changes.
- `docs/progress.md` is the per-feature dev log - one entry per completed
`vX.Y.Z`, with a one-line `Why:`.
- `docs/RELEASE_v0.X.md` is a themed chapter note - write one only when the
middle version number bumps, such as the first `v0.3.0` release. It groups
the `v0.X.0 -> v0.X.N` entries from `progress.md` under user-facing
highlights. Once written, a release file is frozen.
- Bump the middle version (`0.X.0`) when starting a new theme/chapter, not for
every feature. Bump the patch version (`0.X.Y`) for each feature within the
chapter.

## Workflow

- **CLI First**: Every new feature should test in CLI first before UI. Create
`scripts/` or `tests/` using Python when needed.
- **Visual Debugging**: If a UI issue is complex, ask for a screenshot.

## Current Scope

The project is in an early foundation phase.

Built so far:

- Python `uv` workspace.
- `briefly-core` package with config, flag parsing, input resolution, and
briefing request/LLM logic.
- `briefly-cli` package with the `briefly` command shell.
- Root command shape: `briefly [input]`.
- Extract mode for literal text, local files, and stdin.
- Internal briefing request builder for resolved text input.
- LiteLLM-backed briefing with explicit or configured `--model`.
- `briefly config init --model <id>` for first-time config creation.
- SQLite URL and summary cache with TTL, `cache stats`, and `cache clear`.
- Trafilatura-first HTML URL extraction with text/Markdown output and URL
briefing.
- `--stream on|off|auto` token streaming through LiteLLM.
- Structured `--json` output for extract and briefing results.
- YouTube caption briefing through the Android InnerTube player API, with
  clean transcript text and a separate cache slot.
- Groq Whisper fallback for YouTube videos with no captions, using `yt-dlp`
  audio download and `GROQ_API_KEY`.
- Local PDF briefing through pdfplumber, with mtime-keyed extraction cache.
- Placeholder subcommands: `daemon`, `slides`, `transcriber`.
- Tests for CLI help, extract mode, JSON output, streaming, briefing requests,
mocked LLM behavior, flag parsing, input resolution, and config loading.
- README and docs baseline.

## Product Naming

Use Briefly language in code and docs.

Preferred terms:

- `brief`
- `briefing`
- `briefly`
- `Briefly AI`

The hidden root CLI command is named `brief`, because users run:

```bash
briefly https://example.com
```

not:

```bash
briefly brief https://example.com
```

## Project Structure

```text
briefly-ai/
|-- pyproject.toml
|-- uv.lock
|-- AGENTS.md
|-- CLAUDE.md
|-- LICENSE
|-- README.md
|
|-- docs/
|   |-- RELEASE_v0.2.md
|   |-- progress.md
|   |-- tech_spec.md
|   `-- testing.md
|
|-- packages/
|   |-- briefly-core/
|   |   |-- pyproject.toml
|   |   `-- src/briefly_core/
|   |       |-- __init__.py
|   |       |-- briefing.py
|   |       |-- cache.py
|   |       |-- content.py
|   |       |-- config.py
|   |       |-- flags.py
|   |       |-- input.py
|   |       |-- llm.py
|   |       |-- pdf.py
|   |       `-- youtube.py
|   |
|   `-- briefly-cli/
|       |-- pyproject.toml
|       `-- src/briefly_cli/
|           |-- __init__.py
|           |-- main.py
|           `-- commands/
|               |-- __init__.py
|               |-- brief.py
|               |-- cache.py
|               |-- config.py
|               |-- daemon.py
|               |-- slides.py
|               `-- transcriber.py
|
`-- tests/
    |-- cli/
    |   |-- conftest.py
    |   |-- test_cache_cli.py
    |   |-- test_cache_commands.py
    |   |-- test_config_init.py
    |   |-- test_config_model.py
    |   |-- test_extract.py
    |   |-- test_help.py
    |   |-- test_json_output.py
    |   |-- test_pdf_cli.py
    |   |-- test_stream.py
    |   `-- test_youtube_cli.py
    `-- core/
        |-- test_briefing.py
        |-- test_cache.py
        |-- test_content.py
        |-- test_config.py
        |-- test_flags.py
        |-- test_input.py
        |-- test_llm.py
        |-- test_pdf.py
        `-- test_youtube.py
```

## Architecture Rules

- `briefly-core` contains reusable product logic.
- `briefly-cli` owns CLI routing, terminal behavior, and command wiring.
- CLI may import core.
- Core must not import CLI.
- Keep modules small and add folders only when they contain real code.
- Do not add daemon, LLM, extraction, or cache abstractions before their first
working slice exists.

## Config

Briefly config is native to this product:

```text
~/.briefly/config.json
```

On Windows this usually resolves to:

```text
C:\Users\User\.briefly\config.json
```

The environment variable `BRIEFLY_CONFIG` may point to a custom config path.

Current config loader lives in:

```text
packages/briefly-core/src/briefly_core/config.py
```

## CLI Shape

Primary command:

```bash
briefly [input]
```

Examples:

```bash
briefly --help
briefly --version
briefly "some text" --extract
briefly my-file.txt --extract
briefly https://example.com
briefly my-file.txt --length long
briefly daemon --help
briefly slides --help
briefly transcriber setup --help
```

Cleaner Briefly flags are preferred:

- `--extract-only`
- `--output-format`
- `--max-input-chars`
- `--max-tokens`
- `--skip-cache`

Short-term aliases may exist for user convenience, but do not let aliases drive
internal naming.

## Development Workflow

Use `uv` from the repo root.

Because this Windows machine has a broken default uv cache location, commands
should use the workspace-local cache:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check
$env:UV_CACHE_DIR='.uv-cache'; uv run briefly --help
```

Do not assume a manually activated `venv`.

## Verification

After code changes, run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check
```

Expected current baseline:

```text
pytest: 101 passed
ruff: All checks passed
```

## Change Style

- Make small, verifiable changes.
- Prefer clear names over compatibility names.
- Do not add comments that explain migration history.
- Keep comments rare and only for non-obvious behavior.
- Remove unused files, imports, and stale tests when renaming code.
- Keep generated files out of the repo (`__pycache__`, `.venv`, `.uv-cache`,
coverage output, build output).

## Collaboration

The user prefers step-by-step development and discussion.

Before large feature work:

- Explain the next small slice.
- Keep scope narrow.
- Build it.
- Run tests.
- Describe what changed and what remains intentionally unbuilt.
