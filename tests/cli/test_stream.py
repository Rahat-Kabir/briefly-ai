from click.testing import CliRunner
import pytest

from briefly_cli.main import app

runner = CliRunner()


def _fake_stream_factory(chunks):
    async def fake_generate_brief_stream(request, client=None):
        assert request.options.model == "test/model"
        for chunk in chunks:
            yield chunk

    return fake_generate_brief_stream


def test_stream_on_writes_chunks_in_order(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "briefly_cli.commands.brief.generate_brief_stream",
        _fake_stream_factory(["Brief ", "in ", "pieces."]),
    )

    result = runner.invoke(
        app,
        ["Source text.", "--model", "test/model", "--stream", "on"],
        color=False,
    )

    assert result.exit_code == 0
    assert result.output == "Brief in pieces.\n"


def test_stream_on_keeps_trailing_newline(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "briefly_cli.commands.brief.generate_brief_stream",
        _fake_stream_factory(["Done.\n"]),
    )

    result = runner.invoke(
        app,
        ["Source text.", "--model", "test/model", "--stream", "on"],
        color=False,
    )

    assert result.exit_code == 0
    assert result.output == "Done.\n"


def test_stream_off_uses_non_streaming_path(monkeypatch: pytest.MonkeyPatch) -> None:
    streamed = []

    async def fake_generate_brief_stream(request, client=None):
        streamed.append(request)
        yield "should not run"

    async def fake_generate_brief(request, client=None):
        from briefly_core.llm import BriefingResult

        return BriefingResult(text="Whole brief.", model="test/model")

    monkeypatch.setattr(
        "briefly_cli.commands.brief.generate_brief_stream", fake_generate_brief_stream
    )
    monkeypatch.setattr("briefly_cli.commands.brief.generate_brief", fake_generate_brief)

    result = runner.invoke(
        app,
        ["Source text.", "--model", "test/model", "--stream", "off"],
        color=False,
    )

    assert result.exit_code == 0
    assert result.output == "Whole brief.\n"
    assert streamed == []


def test_stream_auto_uses_non_streaming_path_without_tty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    streamed = []

    async def fake_generate_brief_stream(request, client=None):
        streamed.append(request)
        yield "should not run"

    async def fake_generate_brief(request, client=None):
        from briefly_core.llm import BriefingResult

        return BriefingResult(text="Whole brief.", model="test/model")

    monkeypatch.setattr(
        "briefly_cli.commands.brief.generate_brief_stream", fake_generate_brief_stream
    )
    monkeypatch.setattr("briefly_cli.commands.brief.generate_brief", fake_generate_brief)

    result = runner.invoke(
        app,
        ["Source text.", "--model", "test/model", "--stream", "auto"],
        color=False,
    )

    assert result.exit_code == 0
    assert result.output == "Whole brief.\n"
    assert streamed == []


def test_stream_failure_reports_error(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_generate_brief_stream(request, client=None):
        if False:
            yield ""
        raise ValueError("Model returned an empty briefing.")

    monkeypatch.setattr(
        "briefly_cli.commands.brief.generate_brief_stream", fake_generate_brief_stream
    )

    result = runner.invoke(
        app,
        ["Source text.", "--model", "test/model", "--stream", "on"],
        color=False,
    )

    assert result.exit_code != 0
    assert "Model returned an empty briefing." in result.output
