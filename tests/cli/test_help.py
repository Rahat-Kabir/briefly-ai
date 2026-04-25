from click.testing import CliRunner

from briefly_cli.main import app

runner = CliRunner()


def test_root_help() -> None:
    result = runner.invoke(app, ["--help"], color=False)
    assert result.exit_code == 0
    assert "Create concise briefs from text, files, and URLs." in result.output
    assert "--extract-only" in result.output
    assert "--max-input-chars" in result.output
    assert "slides" in result.output
    assert "daemon" in result.output
    assert "transcriber" in result.output


def test_version() -> None:
    result = runner.invoke(app, ["--version"], color=False)
    assert result.exit_code == 0
    assert "briefly 0.1.6" in result.output


def test_command_help() -> None:
    for command in (
        ["slides", "--help"],
        ["daemon", "--help"],
        ["transcriber", "setup", "--help"],
    ):
        result = runner.invoke(app, command, color=False)
        assert result.exit_code == 0


def test_brief_placeholder() -> None:
    result = runner.invoke(app, ["Some text to brief."], color=False)
    assert result.exit_code != 0
    assert "Model is required before briefing can run." in result.output


def test_brief_prints_generated_result(monkeypatch) -> None:
    async def fake_generate_brief(request):
        assert request.text == "Some text to brief."
        return type("Result", (), {"text": "Generated brief."})()

    monkeypatch.setattr("briefly_cli.commands.brief.generate_brief", fake_generate_brief)

    result = runner.invoke(
        app,
        ["Some text to brief.", "--model", "test/model"],
        color=False,
    )

    assert result.exit_code == 0
    assert result.output == "Generated brief.\n"


def test_url_briefing_extracts_then_generates(monkeypatch) -> None:
    async def fake_extract_url(url: str):
        assert url == "https://example.com"
        return type(
            "Extracted",
            (),
            {
                "source": "https://example.com/final",
                "title": "Example Domain",
                "text": "This domain is for examples.",
            },
        )()

    async def fake_generate_brief(request):
        assert request.input_kind == "url"
        assert request.source == "https://example.com/final"
        assert request.text == "Example Domain\n\nThis domain is for examples."
        return type("Result", (), {"text": "Generated URL brief."})()

    monkeypatch.setattr("briefly_cli.commands.brief.extract_url", fake_extract_url)
    monkeypatch.setattr("briefly_cli.commands.brief.generate_brief", fake_generate_brief)

    result = runner.invoke(
        app,
        ["https://example.com", "--model", "test/model"],
        color=False,
    )

    assert result.exit_code == 0
    assert result.output == "Generated URL brief.\n"


def test_root_validates_flags() -> None:
    result = runner.invoke(app, ["https://example.com", "--length", "1"], color=False)
    assert result.exit_code != 0
    assert "Unsupported --length" in result.output
