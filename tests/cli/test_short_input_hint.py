import json

from click.testing import CliRunner
import pytest

from briefly_cli.main import app
from briefly_core.llm import BriefingResult

runner = CliRunner()


def _fake_generate_brief(text: str = "Brief.") -> object:
    async def fake(request):
        return BriefingResult(text=text, model="provider/model")

    return fake


def test_hint_emitted_for_short_input_on_stderr(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "briefly_cli.commands.brief.generate_brief", _fake_generate_brief("Brief output.")
    )

    result = runner.invoke(
        app,
        ["Briefly is short.", "--model", "test/model", "--stream", "off", "--length", "short"],
        color=False,
    )

    assert result.exit_code == 0
    assert "Brief output." in result.stdout
    assert "note: input is 3 words" in result.stderr
    assert "--extract" in result.stderr


def test_hint_suppressed_above_threshold(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "briefly_cli.commands.brief.generate_brief", _fake_generate_brief()
    )

    long_text = " ".join(["word"] * 200)
    result = runner.invoke(
        app,
        [long_text, "--model", "test/model", "--stream", "off", "--length", "short"],
        color=False,
    )

    assert result.exit_code == 0
    assert result.stderr == ""


def test_hint_suppressed_in_extract_mode() -> None:
    result = runner.invoke(
        app,
        ["Briefly is short.", "--extract", "--length", "short"],
        color=False,
    )

    assert result.exit_code == 0
    assert result.stderr == ""


def test_hint_suppressed_in_json_mode_and_stdout_is_valid_json(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "briefly_cli.commands.brief.generate_brief", _fake_generate_brief("Brief output.")
    )

    result = runner.invoke(
        app,
        [
            "Briefly is short.",
            "--model",
            "test/model",
            "--stream",
            "off",
            "--length",
            "short",
            "--json",
        ],
        color=False,
    )

    assert result.exit_code == 0
    assert "note:" not in result.stderr
    payload = json.loads(result.stdout)
    assert payload["summary"] == "Brief output."


def test_hint_suppressed_for_xl_length(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "briefly_cli.commands.brief.generate_brief", _fake_generate_brief()
    )

    result = runner.invoke(
        app,
        ["Briefly is short.", "--model", "test/model", "--stream", "off", "--length", "xl"],
        color=False,
    )

    assert result.exit_code == 0
    assert result.stderr == ""
