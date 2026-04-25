from click.testing import CliRunner

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


def test_extracting_url_fails_clearly_until_url_extraction_exists() -> None:
    result = runner.invoke(app, ["https://example.com", "--extract"], color=False)

    assert result.exit_code != 0
    assert "URL extraction is not implemented yet." in result.output
