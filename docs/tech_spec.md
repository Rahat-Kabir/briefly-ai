# Technical Spec

Briefly AI is a Python product for creating concise briefs. The codebase should
stay Briefly-native in names, docs, config paths, and command wording.

## Architecture

The repo uses a Python `uv` workspace with two packages:

```text
packages/briefly-core
packages/briefly-cli
```

Rules:

- `briefly-core` contains reusable product logic.
- `briefly-cli` owns command routing and terminal behavior.
- CLI may import core.
- Core must not import CLI.
- Add new folders only when they contain real working code.

## CLI

Primary command shape:

```bash
briefly [input]
```

The root input is internally routed to a hidden `brief` command. Users should
not need to type `briefly brief`.

Current visible commands:

```bash
briefly --help
briefly --version
briefly [input]
briefly daemon --help
briefly slides --help
briefly transcriber setup --help
```

Current root command flags include:

- `--extract-only`
- `--output-format`
- `--length`
- `--model`
- `--stream`
- `--max-input-chars`
- `--max-tokens`
- `--skip-cache`

Some short-term aliases exist for convenience. Internal names should still use
Briefly-native terms.

## Briefing Requests

Non-extract input is resolved into a `BriefingRequest` before model calls. The
request stores source kind, text, prompt, model, length, output format, and
input/output limits.

Current behavior:

- Literal text, file text, and stdin can build briefing requests.
- Extracted HTML URL text can build briefing requests.
- Length presets add concrete prompt instructions and default output token caps.
- `--format text` asks for plain text without Markdown formatting.
- `--format markdown` allows Markdown output.
- Empty text is rejected.

## LLM

Briefly uses LiteLLM for real briefing calls. The CLI requires an explicit
`--model` for now and passes the built prompt to `litellm.acompletion`.

Current behavior:

- Text, file, stdin, and HTML URL briefing can call a real model.
- `--max-tokens` forwards to LiteLLM as `max_tokens` and overrides length
  preset defaults.
- Missing model fails with a clear error.
- `--stream on|off|auto` controls token streaming. `auto` streams when stdout
  is a TTY. Streaming uses `litellm.acompletion(stream=True)` and prints
  chunks as plain text.
- Retries, provider presets, and cost reporting are deferred.

## Input Resolution

The root briefing command resolves input before any briefing work starts.

Current supported input kinds:

- `-` reads text from stdin.
- Existing local files are read as UTF-8 text.
- `http` and `https` URLs are fetched when extraction or briefing needs text.
- Any other value is treated as literal text.

`--extract-only` / `--extract` prints resolved text for literal, file, and stdin
input. URL extract mode fetches HTML, removes non-content elements, and prints
title plus page text.

## Config

Default config path:

```text
~/.briefly/config.json
```

Override:

```text
BRIEFLY_CONFIG
```

The config loader currently supports:

- Missing config file.
- JSON parsing.
- Comment rejection.
- Top-level object validation.
- Model shorthand normalization.
- Basic `models`, `output`, `cache`, and `ui` sections.

Model normalization:

```json
"auto"
```

becomes:

```json
{ "mode": "auto" }
```

```json
"openai/gpt-5-mini"
```

becomes:

```json
{ "id": "openai/gpt-5-mini" }
```

```json
"fast"
```

becomes:

```json
{ "name": "fast" }
```

## Deferred Areas

These are intentionally not designed yet:

- Provider presets and config-driven model resolution.
- Cache database/filesystem layout.
- Daemon server and local auth.
- Browser extension API.
- Slides and transcription workflow.

Each area should be introduced as a small tested slice when it becomes the next
implementation target.
