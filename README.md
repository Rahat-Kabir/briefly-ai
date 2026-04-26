# Briefly AI

Python CLI for creating concise briefs from text, files, URLs, and later media
sources.

Current state: early CLI foundation. Briefly can resolve text/file/stdin input,
print extracted text, and generate length-controlled text briefs through
LiteLLM. Config-backed model selection, HTML URL briefing, and token streaming
are available.

## Usage

### Brief text with an LLM

```bash
uv run briefly "Paste or type any text here." --model openai/gpt-4o-mini
uv run briefly "Long article text..." --model openai/gpt-4o-mini --length short
uv run briefly "Long article text..." --model openai/gpt-4o-mini --length long
uv run briefly https://example.com --model openai/gpt-4o-mini
```

`--model` may be a raw model id or a named preset from
`~/.briefly/config.json`:

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
```

### Extract mode

Extract mode resolves and prints input without an LLM call.

```bash
uv run briefly "Some text" --extract
uv run briefly README.md --extract
uv run briefly https://example.com --extract
echo "Piped text" | uv run briefly - --extract
```

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
| `--skip-cache` | Skip cache (not yet implemented) |

## Development

```bash
uv run pytest
uv run ruff check
```

## Project Structure

```text
briefly-ai/
|-- pyproject.toml
|-- README.md
|-- LICENSE
|-- docs/
|   |-- progress.md
|   |-- tech_spec.md
|   `-- testing.md
|-- packages/
|   |-- briefly-core/
|   |   `-- src/briefly_core/
|   |       |-- briefing.py
|   |       |-- content.py
|   |       |-- config.py
|   |       |-- flags.py
|   |       |-- input.py
|   |       `-- llm.py
|   `-- briefly-cli/
|       `-- src/briefly_cli/
|           |-- main.py
|           `-- commands/
|-- tests/
|   |-- cli/
|   `-- core/
`-- uv.lock
```

Docs: [tech spec](docs/tech_spec.md), [progress](docs/progress.md),
[testing](docs/testing.md).

## License

MIT. See [LICENSE](LICENSE).
