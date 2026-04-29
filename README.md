# Briefly AI

Python CLI for creating concise briefs from text, files, URLs, and later media
sources.

Current state: early CLI foundation. Briefly can resolve text/file/stdin input,
print extracted text, and generate length-controlled text briefs through
LiteLLM. Config-backed model selection, trafilatura-backed HTML URL briefing,
YouTube caption briefing, Groq Whisper fallback, token streaming, structured
JSON output, and local cache are available. YouTube transcript timestamps are
available in extract and briefing input.

## Usage

### Brief text with an LLM

```bash
uv run briefly "Paste or type any text here." --model openai/gpt-4o-mini
uv run briefly "Long article text..." --model openai/gpt-4o-mini --length short
uv run briefly "Long article text..." --model openai/gpt-4o-mini --length long
uv run briefly https://example.com --model openai/gpt-4o-mini
```

Create a default config once:

```bash
uv run briefly config init --model openai/gpt-4o-mini
```

This writes `~/.briefly/config.json` and refuses to overwrite it unless
`--force` is passed. `--model` may also be a named preset from that file:

```json
{
  "model": "openai/gpt-4o-mini",
  "models": {
    "fast": "openai/gpt-4o-mini"
  }
}
```

### Brief a file

```bash
uv run briefly notes.txt --model openai/gpt-4o-mini
uv run briefly paper.pdf --model openai/gpt-4o-mini
uv run briefly paper.pdf --extract
```

PDF input uses pdfplumber; the title comes from PDF metadata when present,
otherwise the filename. Scanned/image-only PDFs raise a clear error.

### Brief a YouTube video

```bash
uv run briefly https://youtu.be/v4F1gFy-hqg --model openai/gpt-4o-mini
uv run briefly https://www.youtube.com/watch?v=v4F1gFy-hqg --extract
uv run briefly https://www.youtube.com/watch?v=v4F1gFy-hqg --extract --timestamps
uv run briefly https://youtu.be/v4F1gFy-hqg --extract --json
```

Briefly fetches the video's captions through YouTube's Android InnerTube API.
Works for `youtube.com`, `youtu.be`, `/shorts`, `/embed`, and `/live` URLs.
Use `--timestamps` to print transcript lines with `[m:ss]` or `[h:mm:ss]`
timestamps.

If YouTube captions are missing, Briefly can fall back to Groq Whisper. Install
`yt-dlp` and set `GROQ_API_KEY`:

```powershell
$env:GROQ_API_KEY='your_groq_api_key'
uv run briefly "https://youtu.be/example" --extract
```

### Extract mode

Extract mode resolves and prints input without an LLM call.

```bash
uv run briefly "Some text" --extract
uv run briefly README.md --extract
uv run briefly https://example.com --extract
uv run briefly https://example.com --extract --json
echo "Piped text" | uv run briefly - --extract
```

URL extraction uses trafilatura first, with BeautifulSoup fallback. Use
`--output-format markdown` to preserve Markdown-style headings and links.

### Options

```bash
uv run briefly --help
```

| Flag | Description |
|------|-------------|
| `--extract` | Print resolved input without briefing |
| `--model TEXT` | LLM model id or configured model preset |
| `--length TEXT` | Brief length: `short`, `medium`, `long`, `xl`, `xxl`, or a char count like `500` |
| `--output-format TEXT` | Output format: `text` or `markdown` |
| `--max-input-chars TEXT` | Truncate input to this many characters, e.g. `50k` |
| `--max-tokens TEXT` | Maximum output tokens |
| `--stream TEXT` | Streaming mode: `on`, `off`, or `auto` (TTY) |
| `--json` | Print structured JSON; streaming is disabled in JSON mode |
| `--timestamps` | Include YouTube transcript timestamps when available |
| `--skip-cache` | Skip cache reads and writes |

### Cache

Briefly stores URL extraction and summary results in `~/.briefly/cache.sqlite`.

```bash
uv run briefly cache stats
uv run briefly cache clear
uv run briefly https://example.com --skip-cache
```

Default TTLs: URL extraction cache expires after 7 days; summary cache expires
after 30 days. Override both with:

```json
{
  "cache": {
    "ttlDays": 14
  }
}
```

## Development

```bash
uv run pytest
uv run ruff check
```

On Windows, use the repo-local uv cache if the default cache fails:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check
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
|-- tests/
|   |-- cli/
|   |   |-- conftest.py
|   |   |-- test_cache_cli.py
|   |   |-- test_cache_commands.py
|   |   |-- test_config_init.py
|   |   |-- test_config_model.py
|   |   |-- test_extract.py
|   |   |-- test_help.py
|   |   |-- test_json_output.py
|   |   |-- test_pdf_cli.py
|   |   |-- test_stream.py
|   |   `-- test_youtube_cli.py
|   `-- core/
|       |-- test_briefing.py
|       |-- test_cache.py
|       |-- test_content.py
|       |-- test_config.py
|       |-- test_flags.py
|       |-- test_input.py
|       |-- test_llm.py
|       |-- test_pdf.py
|       `-- test_youtube.py
```

Docs: [tech spec](docs/tech_spec.md), [progress](docs/progress.md),
[testing](docs/testing.md).

## License

MIT. See [LICENSE](LICENSE).
