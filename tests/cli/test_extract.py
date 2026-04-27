from click.testing import CliRunner
import pytest

from briefly_cli.main import app

runner = CliRunner()


def test_extracts_literal_text() -> None:
    result = runner.invoke(app, ["Briefly reads text.", "--extract"], color=False)

    assert result.exit_code == 0
    assert result.output == "Briefly reads text.\n"


def test_extracts_local_file() -> None:
    with runner.isolated_filesystem():
        with open("notes.txt", "w", encoding="utf-8") as file:
            file.write("Briefly reads files.")

        result = runner.invoke(app, ["notes.txt", "--extract"], color=False)

    assert result.exit_code == 0
    assert result.output == "Briefly reads files.\n"


def test_extracts_stdin() -> None:
    result = runner.invoke(app, ["-", "--extract"], input="Briefly reads stdin.", color=False)

    assert result.exit_code == 0
    assert result.output == "Briefly reads stdin.\n"


def test_extracts_url(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_extract_url(url: str, **kwargs):
        assert url == "https://example.com"
        return type(
            "Extracted",
            (),
            {
                "source": "https://example.com",
                "title": "Example Domain",
                "text": "This domain is for examples.",
            },
        )()

    monkeypatch.setattr("briefly_cli.commands.brief.extract_url", fake_extract_url)

    result = runner.invoke(app, ["https://example.com", "--extract"], color=False)

    assert result.exit_code == 0
    assert result.output == "Example Domain\n\nThis domain is for examples.\n"


def test_extracts_url_as_markdown(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_extract_url(url: str, **kwargs):
        assert kwargs["output_format"] == "markdown"
        return type(
            "Extracted",
            (),
            {
                "source": "https://example.com",
                "title": "Example Domain",
                "text": "# Heading\n\nA [link](https://example.com).",
            },
        )()

    monkeypatch.setattr("briefly_cli.commands.brief.extract_url", fake_extract_url)

    result = runner.invoke(
        app,
        ["https://example.com", "--extract", "--output-format", "markdown"],
        color=False,
    )

    assert result.exit_code == 0
    assert result.output == "Example Domain\n\n# Heading\n\nA [link](https://example.com).\n"


def test_url_extract_errors_are_clear(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_extract_url(url: str, **kwargs):
        raise ValueError("URL did not return HTML content: application/json")

    monkeypatch.setattr("briefly_cli.commands.brief.extract_url", fake_extract_url)

    result = runner.invoke(app, ["https://example.com/data.json", "--extract"], color=False)

    assert result.exit_code != 0
    assert "URL did not return HTML content: application/json" in result.output
