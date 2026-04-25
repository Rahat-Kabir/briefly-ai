# Briefly AI

Python CLI for concise briefs from text, files, URLs, and later media sources.

Current state: early CLI foundation. Briefly can resolve text/file/stdin input,
print extracted text, and generate a real text brief through LiteLLM. URL
extraction is not implemented yet.

## Usage

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run briefly --help
$env:UV_CACHE_DIR='.uv-cache'; uv run briefly "Text to inspect." --extract
$env:UV_CACHE_DIR='.uv-cache'; uv run briefly README.md --extract
"Text from stdin." | uv run briefly - --extract
$env:UV_CACHE_DIR='.uv-cache'; uv run briefly "Text to brief." --model openai/gpt-4o-mini
```

## Development

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check
```

## Structure

```text
packages/briefly-core/src/briefly_core/
  briefing.py
  config.py
  flags.py
  input.py
  llm.py
packages/briefly-cli/src/briefly_cli/
  main.py
  commands/
tests/
  cli/
  core/
docs/
```

Docs: [tech spec](docs/tech_spec.md), [progress](docs/progress.md),
[testing](docs/testing.md).

## License

MIT. See [LICENSE](LICENSE).
