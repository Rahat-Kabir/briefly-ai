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
briefly cache stats
briefly cache clear
briefly config init --model <model-id>
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
- `--json`
- `--timestamps`

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

Briefly uses LiteLLM for real briefing calls. The CLI resolves a model before
calling `litellm.acompletion`.

Current behavior:

- Text, file, stdin, and HTML URL briefing can call a real model.
- Model resolution order is raw `--model`, named `--model` preset, top-level
  config `model`, then the existing missing-model error.
- `--max-tokens` forwards to LiteLLM as `max_tokens` and overrides length
  preset defaults.
- Missing model fails with a clear error.
- `--stream on|off|auto` controls token streaming. `auto` streams when stdout
  is a TTY. Streaming uses `litellm.acompletion(stream=True)` and prints
  chunks as plain text.
- `--json` prints structured input, extracted text, prompt, model, cache, and
  summary fields. Streaming is disabled in JSON mode so stdout stays valid JSON.
- Retries, provider presets, and cost reporting are deferred.

## Input Resolution

The root briefing command resolves input before any briefing work starts.

Current supported input kinds:

- `-` reads text from stdin.
- Existing local files are read as UTF-8 text.
- `http` and `https` URLs are fetched when extraction or briefing needs text.
- Any other value is treated as literal text.

`--extract-only` / `--extract` prints resolved text for literal, file, and stdin
input. URL extract mode fetches HTML, removes non-content elements, extracts
main text with trafilatura first, falls back to BeautifulSoup, and prints title
plus page text. `--output-format markdown` preserves Markdown-style headings
and links where available.

## YouTube

YouTube URLs (`youtube.com`, `youtu.be`, `youtube-nocookie.com`) are routed to a
captions extractor instead of the HTML extractor.

Flow:

- Parse the video id from `watch?v=`, `youtu.be/`, `/shorts/`, `/embed/`, or
  `/live/` URLs.
- POST to `youtubei/v1/player` as the Android client with a hardcoded public
  InnerTube key. Skips the watch page so YouTube's bot detection on `/watch`
  does not block the request.
- Pick a caption track: manual before auto-generated, English first, dedupe by
  language.
- Strip `fmt=srv3` from the caption `baseUrl` so YouTube serves the older XML
  format with `<text>` elements.
- Parse XML segments and run `html.unescape` to decode double-encoded entities.
- Return a `YoutubeTranscript` with title, language, segments, and joined text.
- `--timestamps` formats transcript segments as timed lines for extract output
  and for the text sent into the briefing request.

Watch-page fallback runs only when the Android call returns no captions. It
scrapes a fresh `INNERTUBE_API_KEY` and retries, in case the hardcoded key is
ever rotated.

Cache uses a separate `youtube_transcript` slot from regular URL extraction so
future YouTube extractor changes do not collide with HTML article entries.
Plain and timestamped transcript output use separate cache keys.

Failures raise clear errors: unsupported URL, no captions available, empty
caption track, missing caption URL.

## Cache

Briefly stores cache data in:

```text
~/.briefly/cache.sqlite
```

If `BRIEFLY_CONFIG` points to a custom config file, cache is stored beside that
file as `cache.sqlite`.

Current behavior:

- URL extraction cache avoids repeated URL fetch/extract work.
- Summary cache avoids repeated model calls for the same input/model/options.
- URL cache keys include output format, so text and Markdown entries are
  separate.
- `--skip-cache` bypasses cache reads and writes.
- URL entries expire after 7 days by default.
- Summary entries expire after 30 days by default.
- Config `cache.ttlDays` overrides both TTLs.
- `briefly cache stats` shows path, entry counts, and size.
- `briefly cache clear` removes cache rows and keeps the SQLite file.

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
- CLI model resolution from top-level `model` and named `models` presets.
- `cache.ttlDays` for cache freshness.
- `briefly config init --model <id>` creates the config file and refuses
  overwrite unless `--force` is passed.

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

- Provider-specific behavior.
- Daemon server and local auth.
- Browser extension API.
- Slides and transcription workflow.

Each area should be introduced as a small tested slice when it becomes the next
implementation target.
