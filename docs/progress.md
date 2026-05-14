# Progress

This is the development log for Briefly AI.

PyPI package versions are the only versions. Active work belongs under the next
chosen `Unreleased` package version. Do not create internal `vX.Y.Z` feature
milestones.

## v0.2.0 - Unreleased

Why: expand Briefly beyond text, URLs, YouTube captions, and PDFs into richer
local inputs while keeping the CLI-first workflow simple.

Completed:

- Added local audio/video transcription and briefing through Groq Whisper.
- Added `briefly_core/audio.py` with shared Groq transcription helpers.
- Routed local audio/video paths through `audio` and `video` input kinds.
- Reused the shared Groq helper from YouTube's no-caption fallback.
- Added direct local media transcript caching by path, mtime, size, and model.
- Added clear errors for missing `GROQ_API_KEY`, oversized files, unsupported
  media types, rate limits, and empty Groq responses.
- Added core and CLI tests for local media extract, briefing, JSON, cache,
  invalidation, and skip-cache paths.
- Added a short-input hint on stderr when resolved input is already at or below
  the word-count threshold for the requested length preset (short 80, medium
  180, long 350), suggesting `--extract` while still running the brief.
  Suppressed in `--extract`, `--json`, and `xl`/`xxl` lengths.
- Migrated CLI tests from `result.output` to `result.stdout`/`result.stderr` to
  match Click 8.3's separate stream capture.

Possible before release:

- Save generated briefs to Markdown files.
- Polish media error messages after real-world testing.
- Small bug fixes found while dogfooding.

Not built yet:

- Audio extraction or chunking for large media.
- Speaker labels, timestamps, subtitles, or batch transcription.
- Non-Groq transcription providers.

## v0.1.0 - Published

Why: first public PyPI release of the Briefly AI CLI foundation.

Completed:

- Created the Python `uv` workspace with `briefly-core` and `briefly-cli`.
- Added the `briefly [input]` command shape with hidden root `brief` command.
- Added Briefly-native config loading at `~/.briefly/config.json`.
- Added text, local file, stdin, URL, YouTube, and PDF input flows.
- Added LiteLLM-backed briefing with explicit or configured model selection.
- Added length controls, text/Markdown output, token streaming, and structured
  JSON output.
- Added `--brief-type standard|executive|action|study|decision`.
- Added HTML extraction through trafilatura with BeautifulSoup fallback.
- Added YouTube caption extraction through Android InnerTube, timestamp output,
  and Groq Whisper fallback for videos without captions.
- Added local and remote PDF extraction through pdfplumber.
- Added SQLite URL extraction, transcript, PDF, and summary caching with TTL,
  `cache stats`, `cache clear`, and `--skip-cache`.
- Added placeholder `daemon`, `slides`, and `transcriber` commands.
- Added README, technical spec, testing docs, release docs, and public
  changelog baseline.
