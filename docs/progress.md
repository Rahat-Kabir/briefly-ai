# Progress

This is the per-feature development log. Add one entry per completed version.

## v0.1.8 - Config Model Resolution

Why: let users set a default model once instead of passing `--model` every run.

Completed:

- Loaded Briefly config in the root briefing command.
- Resolved raw model ids, named `models` presets, and top-level default `model`.
- Added CLI tests for default, named, override, missing, and unknown model cases.

Not built yet:

- Config file creation command.
- Cache storage.
- Daemon server.
- Browser extension integration.
- Slides/transcription implementation.

## v0.1.7 - Streaming Output

Why: print tokens as they arrive and clear the parsed-but-unused `--stream`
flag.

Completed:

- Added `generate_brief_stream` and `LiteLlmBriefingClient.stream` using
  `litellm.acompletion(stream=True)`.
- Wired `--stream on|off|auto` in the CLI; `auto` streams when stdout is a TTY.
- Added core and CLI tests for chunk order, trailing newline, off/auto paths,
  and stream errors.

Not built yet:

- Cache storage.
- Daemon server.
- Browser extension integration.
- Slides/transcription implementation.

## v0.1.6 - URL Briefing

Why: let URL input use the existing LiteLLM briefing pipeline.

Completed:

- Wired URL briefing to extract HTML before building a briefing request.
- Added tests for URL extraction feeding generated briefing output.

Not built yet:

- Streaming output.
- Cache storage.
- Daemon server.
- Browser extension integration.
- Slides/transcription implementation.

## v0.1.5 - URL Extract Mode

Why: make URL input produce page text before summarizing URLs.

Completed:

- Added HTML URL extraction with `httpx` and BeautifulSoup.
- Added `--extract` support for URL input.
- Added tests for HTML parsing, non-HTML failures, empty pages, and CLI output.

Not built yet:

- Streaming output.
- Cache storage.
- Daemon server.
- Browser extension integration.
- Slides/transcription implementation.

## v0.1.4 - Brief Controls

Why: make length and output-format flags shape model output predictably.

Completed:

- Added prompt profiles for `short`, `medium`, `long`, `xl`, and `xxl`.
- Added default token caps for length presets.
- Kept explicit `--max-tokens` as the override.
- Made text output ask for no Markdown formatting.
- Added tests for prompt and token behavior.

Not built yet:

- URL extraction.
- Streaming output.
- Cache storage.
- Daemon server.
- Browser extension integration.
- Slides/transcription implementation.

## v0.1.3 - LiteLLM Briefing

Why: make resolved text input produce a real model-backed brief.

Completed:

- Added LiteLLM as the first LLM dependency.
- Added `BriefingResult`, `BriefingClient`, and `LiteLlmBriefingClient`.
- Wired the CLI to call LiteLLM for non-extract text briefing.
- Required explicit `--model` before real briefing calls.
- Added mocked tests for the LLM client and CLI output.
- Added MIT license.

Not built yet:

- URL extraction.
- Streaming output.
- Cache storage.
- Daemon server.
- Browser extension integration.
- Slides/transcription implementation.

## v0.1.2 - Briefing Request

Why: define the internal request shape before adding an LLM provider.

Completed:

- Added `BriefingOptions` and `BriefingRequest`.
- Added prompt construction for resolved text input.
- Wired the CLI to build requests before placeholder briefing output.
- Added tests for request creation, truncation, format/length preservation, and
  unsupported URL briefing.

Not built yet:

- LLM calls.
- URL extraction.
- Cache storage.
- Daemon server.
- Browser extension integration.
- Slides/transcription implementation.

## v0.1.1 - Input Resolver

Why: create the first usable CLI slice by resolving text input before adding
LLM or URL extraction work.

Completed:

- Added core input resolution for literal text, local text files, stdin, and URL
  detection.
- Wired `--extract-only` / `--extract` to print resolved text.
- Added a clear URL extraction placeholder error.
- Added tests for core input resolution and CLI extract mode.

Not built yet:

- LLM calls.
- URL extraction.
- Cache storage.
- Daemon server.
- Browser extension integration.
- Slides/transcription implementation.

## v0.1.0 - Foundation

Why: establish a clean Briefly-native Python base before adding LLM, extraction,
daemon, or media features.

Completed:

- Created `uv` workspace.
- Added `briefly-core` and `briefly-cli`.
- Added `briefly [input]` command shape.
- Added hidden root `brief` command.
- Added placeholder `daemon`, `slides`, and `transcriber` commands.
- Added Briefly-native config loader at `~/.briefly/config.json`.
- Added flag parsing.
- Added tests for CLI help, config loading, and flags.
- Added lint/test workflow.
- Added README and docs baseline.

Not built yet:

- LLM calls.
- Content extraction.
- Cache storage.
- Daemon server.
- Browser extension integration.
- Slides/transcription implementation.
