# Progress

This is the per-feature development log. Add one entry per completed version.

## v0.3.1 - PDF URL Input

Why: let remote PDF links use the same text extraction path as local PDFs.

Completed:

- Added `extract_pdf_bytes` so PDF extraction can run from downloaded bytes.
- Routed URL responses with `application/pdf` through pdfplumber.
- Routed `.pdf` response URLs through pdfplumber even with generic content type.
- Added URL filename title fallback when PDF metadata has no title.
- Added tests for PDF content type, generic `.pdf` URL, and empty PDF errors.

Not built yet:

- Native OpenAI PDF attachment for higher-fidelity briefing.
- OCR for scanned/image-only PDFs.
- Word/Excel/PowerPoint document input.

## v0.3.0 - PDF Input

Why: brief local PDF files using their text layer.

Completed:

- Added `briefly_core/pdf.py` with `extract_pdf` using pdfplumber.
- Routed `.pdf` paths through a new `pdf` input kind without reading bytes
  upfront.
- Added a CLI PDF branch with cache slot `pdf_extract` keyed by absolute path
  and file `mtime_ns`, so editing a PDF auto-invalidates the cache.
- Title falls back from PDF metadata to filename stem.
- Empty/scanned PDFs raise a clear "no extractable text" error.
- Added 5 core and 6 CLI tests; PDF fixtures are hand-built to avoid extra
  test dependencies.

Not built yet:

- Native OpenAI PDF attachment for higher-fidelity briefing.
- OCR for scanned/image-only PDFs.
- Word/Excel/PowerPoint document input.

## v0.2.2 - Groq Whisper YouTube Fallback

Why: support YouTube videos that have no accessible caption track.

Completed:

- Added a YouTube fallback path after Android captions and watch-page key retry.
- Downloads audio with `yt-dlp` when `GROQ_API_KEY` is set.
- Sends audio to Groq's OpenAI-compatible transcription endpoint.
- Uses `whisper-large-v3-turbo` by default.
- Keeps Groq segments compatible with existing timestamp output.
- Added tests for no-key behavior, Groq fallback success, and fallback errors.

Not built yet:

- Subtitle-only yt-dlp fallback before audio transcription.
- Local Whisper fallback.
- Daemon server.
- Browser extension integration.
- Slides/transcription implementation.

## v0.2.1 - YouTube Timestamps

Why: let users keep video timing while extracting or briefing YouTube captions.

Completed:

- Added `--timestamps` to the root briefing command.
- Formatted YouTube transcript segments as `[m:ss]` or `[h:mm:ss]` lines.
- Kept plain and timestamped YouTube transcript cache entries separate.
- Added core, CLI, JSON, help, and cache tests for timestamped transcripts.

Not built yet:

- `--language` and `--youtube` mode flag.
- yt-dlp + audio transcription for videos without captions.
- Daemon server.
- Browser extension integration.
- Slides/transcription implementation.

## v0.2.0 - YouTube Captions

Why: brief YouTube videos directly using their captions, without scraping the
watch page.

Completed:

- Added `briefly_core/youtube.py`: URL detection, video-id parsing, Android
  InnerTube player call, caption track picker, XML parsing, orchestrator.
- Routed YouTube URLs through the new extractor with their own cache slot.
- Stripped `fmt=srv3` from caption URLs so the parser gets the `<text>` format.
- Decoded double-encoded HTML entities so transcript output is clean.
- Watch-page fallback only when the hardcoded Android key returns no captions.
- Added 23 core tests and 5 CLI tests.

Not built yet:

- yt-dlp + audio transcription for videos without captions.
- `--language`, `--youtube` mode flag.
- Daemon server.
- Browser extension integration.
- Slides/transcription implementation.

## v0.1.13 - Structured JSON Output

Why: make CLI extract and briefing results easier to test and consume from tools.

Completed:

- Added `--json` to the root briefing command.
- Returned structured input, extracted text, prompt, LLM, cache, and summary
  fields for JSON output.
- Disabled token streaming in JSON mode so stdout stays valid JSON.
- Added CLI tests for extract JSON, briefing JSON, cache hits, and stream mode.

Not built yet:

- Daemon server.
- Browser extension integration.
- Slides/transcription implementation.

## v0.1.12 - Markdown URL Extraction

Why: preserve useful article structure such as headings and links during URL extraction.

Completed:

- Added Markdown URL extraction through trafilatura and markdownify fallback.
- Wired `--output-format markdown` into URL extract and briefing paths.
- Separated text and Markdown URL cache keys.
- Added tests for Markdown extraction, fallback, cache keys, and briefing input.

Not built yet:

- Daemon server.
- Browser extension integration.
- Slides/transcription implementation.

## v0.1.11 - Primary Article Extraction

Why: make URL briefs cleaner by extracting main article text before fallback text scraping.

Completed:

- Added trafilatura as the primary HTML article extractor.
- Kept BeautifulSoup extraction as fallback.
- Preserved HTML title behavior and non-content element cleanup.
- Added tests for primary extraction and fallback.

Not built yet:

- Daemon server.
- Browser extension integration.
- Slides/transcription implementation.

## v0.1.10 - Cache Storage

Why: avoid repeated URL extraction and model calls for identical requests.

Completed:

- Added SQLite URL and summary cache at `~/.briefly/cache.sqlite`.
- Wired `--skip-cache` to bypass cache reads and writes.
- Added TTLs: 7 days for URL extraction, 30 days for summaries, or
  `cache.ttlDays` from config.
- Added `briefly cache stats` and `briefly cache clear`.
- Added core and CLI cache tests.

Not built yet:

- Daemon server.
- Browser extension integration.
- Slides/transcription implementation.

## v0.1.9 - Config Init Command

Why: make first-time model config setup explicit and repeatable.

Completed:

- Added `briefly config init --model <id>`.
- Created config parent directories and refused overwrite unless `--force`.
- Added CLI tests for create, overwrite, force, invalid model, and missing path.

Not built yet:

- Daemon server.
- Browser extension integration.
- Slides/transcription implementation.

## v0.1.8 - Config Model Resolution

Why: let users set a default model once instead of passing `--model` every run.

Completed:

- Loaded Briefly config in the root briefing command.
- Resolved raw model ids, named `models` presets, and top-level default `model`.
- Added CLI tests for default, named, override, missing, and unknown model cases.

Not built yet:

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
