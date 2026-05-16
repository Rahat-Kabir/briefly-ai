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
- PyPI package versions are the only versions. Do not create internal `vX.Y.Z`
feature milestones.
- `docs/progress.md` is the development log. Keep active work under the next
chosen `Unreleased` package version, such as `v0.2.0 - Unreleased`, with a
one-line `Why:`.
- `CHANGELOG.md` is for public package releases only. Update it during release
preparation, not for every feature.
- Keep `pyproject.toml` versions at the latest published PyPI version until
the user explicitly asks to prepare a release.
- Choose the next version only when the user decides the release target. Use
patch versions for bugfix releases and minor versions for larger feature
releases.
- Do not create `docs/RELEASE_v0.X.md` files unless the user explicitly asks
for themed release notes during release preparation.
- For public package releases, follow `docs/release.md`.
- Do not bump package versions, create git tags, or publish to TestPyPI/PyPI
without explicit user approval.

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
- `--brief-type standard|executive|action|study|decision` prompt shaping,
  with `standard` preserving existing behavior.
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
- Local and remote PDF briefing through pdfplumber, with mtime-keyed cache for
  local PDFs.
- Local audio/video transcription and briefing through Groq Whisper, with
  mtime/size/model-keyed transcript cache.
- Local image briefing (`.png`, `.jpg`, `.jpeg`, `.webp`, `.gif`) through a
  vision LLM, with optional `vision.model` config block, `--vision-model`
  flag, and mtime/size/model-keyed extract cache.
- Short-input hint on stderr when input is already at or below the threshold
  for the requested length preset; the brief still runs.
- Placeholder subcommands: `daemon`, `slides`, `transcriber`.
- Tests for CLI help, extract mode, JSON output, streaming, briefing requests,
mocked LLM behavior, flag parsing, input resolution, media transcription, and
config loading.
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
|-- CHANGELOG.md
|-- LICENSE
|-- README.md
|
|-- assets/
|   |-- briefly-ai-hero.png
|   `-- diagrams/           # Mermaid source and rendered SVG diagrams
|
|-- docs/
|   |-- progress.md
|   |-- release.md
|   |-- tech_spec.md
|   `-- testing.md
|
|-- packages/
|   |-- briefly-core/
|   |   |-- pyproject.toml
|   |   `-- src/briefly_core/
|   |       |-- __init__.py
|   |       |-- audio.py
|   |       |-- briefing.py
|   |       |-- cache.py
|   |       |-- content.py
|   |       |-- config.py
|   |       |-- flags.py
|   |       |-- image.py
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
    |   |-- test_image_cli.py
    |   |-- test_json_output.py
    |   |-- test_media_cli.py
    |   |-- test_pdf_cli.py
    |   |-- test_stream.py
    |   `-- test_youtube_cli.py
    `-- core/
        |-- test_audio.py
        |-- test_briefing.py
        |-- test_cache.py
        |-- test_content.py
        |-- test_config.py
        |-- test_flags.py
        |-- test_image.py
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
briefly meeting.txt --brief-type action
briefly meeting.mp3 --extract
briefly lecture.mp4 --brief-type study
briefly screenshot.png --extract
briefly slide.jpg --brief-type study --vision-model gemini/gemini-2.5-flash-lite
briefly daemon --help
briefly slides --help
briefly transcriber setup --help
```

Cleaner Briefly flags are preferred:

- `--extract-only`
- `--output-format`
- `--brief-type`
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
pytest: 204 passed
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
