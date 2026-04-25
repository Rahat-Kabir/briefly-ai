# Briefly AI

Python CLI for creating concise briefs from text, files, URLs, and later media
sources.

Current state: early CLI foundation. Briefly can resolve text/file/stdin input,
print extracted text, and generate a real text brief through LiteLLM. URL
extraction is not implemented yet.

## Usage

```bash
uv run briefly --help
uv run briefly "Text to inspect." --extract
uv run briefly README.md --extract
echo "Text from stdin." | uv run briefly - --extract
uv run briefly "Text to brief." --model openai/gpt-4o-mini
uv run briefly "Text to brief." --model openai/gpt-4o-mini --length short
```

## Development

```bash
uv run pytest
uv run ruff check
```

## Project Structure

```text
briefly-ai/
├── pyproject.toml                  # Workspace config, dev dependencies
├── README.md
├── LICENSE
│
├── docs/
│   ├── progress.md                 # Per-version dev log
│   ├── tech_spec.md                # Technical specification
│   └── testing.md                  # Test coverage and workflow
│
├── packages/
│   ├── briefly-core/               # Reusable product logic (no CLI dependency)
│   │   └── src/briefly_core/
│   │       ├── __init__.py
│   │       ├── briefing.py         # Briefing request and prompt builder
│   │       ├── config.py           # Config loader (~/.briefly/config.json)
│   │       ├── flags.py            # CLI flag parsing and validation
│   │       ├── input.py            # Input resolution (text, file, stdin, URL)
│   │       └── llm.py              # LiteLLM-backed briefing client
│   │
│   └── briefly-cli/                # CLI routing and terminal behavior
│       └── src/briefly_cli/
│           ├── __init__.py
│           ├── main.py             # Entry point and command group
│           └── commands/
│               ├── __init__.py
│               ├── brief.py        # Main briefing command (hidden root)
│               ├── daemon.py       # Placeholder: local daemon
│               ├── slides.py       # Placeholder: slide extraction
│               └── transcriber.py  # Placeholder: transcription tools
│
└── tests/
    ├── cli/
    │   ├── test_extract.py         # Extract mode tests
    │   └── test_help.py            # CLI help and version tests
    └── core/
        ├── test_briefing.py        # Briefing request and prompt tests
        ├── test_config.py          # Config loading and validation tests
        ├── test_flags.py           # Flag parsing tests
        ├── test_input.py           # Input resolution tests
        └── test_llm.py             # LLM client tests (mocked)
```

Docs: [tech spec](docs/tech_spec.md), [progress](docs/progress.md),
[testing](docs/testing.md).

## License

MIT. See [LICENSE](LICENSE).
