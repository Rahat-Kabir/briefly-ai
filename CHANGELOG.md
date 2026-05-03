# Changelog

Public release notes for Briefly AI.

## 0.1.0 - 2026-05-03

First public PyPI release.

Added:

- `briefly` CLI command through the `briefly-ai` package.
- Text, local file, stdin, URL, PDF, and YouTube briefing.
- LiteLLM-backed model calls with explicit or configured model selection.
- `briefly config init --model <id>` for first-time model setup.
- Brief types: `standard`, `executive`, `action`, `study`, and `decision`.
- Extract mode for resolved input without an LLM call.
- Structured `--json` output.
- Token streaming with `--stream on|off|auto`.
- SQLite URL, PDF, YouTube transcript, and summary cache.
- YouTube captions through Android InnerTube, timestamp output, and Groq
  Whisper fallback when captions are unavailable.
- Local and remote PDF text extraction through pdfplumber.
