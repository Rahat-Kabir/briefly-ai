import json
from pathlib import Path

from click.testing import CliRunner

from briefly_cli.main import app

runner = CliRunner()


def _write_config(tmp_path: Path, value: object) -> Path:
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(value), encoding="utf-8")
    return config_path


def test_uses_default_model_from_config(monkeypatch, tmp_path: Path) -> None:
    config_path = _write_config(tmp_path, {"model": "test/default"})
    monkeypatch.setenv("BRIEFLY_CONFIG", str(config_path))

    async def fake_generate_brief(request):
        assert request.options.model == "test/default"
        return type("Result", (), {"text": "Configured brief."})()

    monkeypatch.setattr("briefly_cli.commands.brief.generate_brief", fake_generate_brief)

    result = runner.invoke(app, ["Source text."], color=False)

    assert result.exit_code == 0
    assert result.output == "Configured brief.\n"


def test_uses_named_default_model_from_config(monkeypatch, tmp_path: Path) -> None:
    config_path = _write_config(tmp_path, {"model": "fast", "models": {"fast": "test/fast"}})
    monkeypatch.setenv("BRIEFLY_CONFIG", str(config_path))

    async def fake_generate_brief(request):
        assert request.options.model == "test/fast"
        return type("Result", (), {"text": "Named default brief."})()

    monkeypatch.setattr("briefly_cli.commands.brief.generate_brief", fake_generate_brief)

    result = runner.invoke(app, ["Source text."], color=False)

    assert result.exit_code == 0
    assert result.output == "Named default brief.\n"


def test_resolves_named_model_preset_from_option(monkeypatch, tmp_path: Path) -> None:
    config_path = _write_config(tmp_path, {"models": {"fast": "test/fast"}})
    monkeypatch.setenv("BRIEFLY_CONFIG", str(config_path))

    async def fake_generate_brief(request):
        assert request.options.model == "test/fast"
        return type("Result", (), {"text": "Fast brief."})()

    monkeypatch.setattr("briefly_cli.commands.brief.generate_brief", fake_generate_brief)

    result = runner.invoke(app, ["Source text.", "--model", "fast"], color=False)

    assert result.exit_code == 0
    assert result.output == "Fast brief.\n"


def test_explicit_model_id_overrides_config(monkeypatch, tmp_path: Path) -> None:
    config_path = _write_config(
        tmp_path,
        {"model": "test/default", "models": {"fast": "test/fast"}},
    )
    monkeypatch.setenv("BRIEFLY_CONFIG", str(config_path))

    async def fake_generate_brief(request):
        assert request.options.model == "override/model"
        return type("Result", (), {"text": "Override brief."})()

    monkeypatch.setattr("briefly_cli.commands.brief.generate_brief", fake_generate_brief)

    result = runner.invoke(app, ["Source text.", "--model", "override/model"], color=False)

    assert result.exit_code == 0
    assert result.output == "Override brief.\n"


def test_missing_model_keeps_required_model_error(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("BRIEFLY_CONFIG", str(tmp_path / "missing.json"))

    result = runner.invoke(app, ["Source text."], color=False)

    assert result.exit_code != 0
    assert "Model is required before briefing can run." in result.output


def test_unknown_model_preset_reports_error(monkeypatch, tmp_path: Path) -> None:
    config_path = _write_config(tmp_path, {"models": {"fast": "test/fast"}})
    monkeypatch.setenv("BRIEFLY_CONFIG", str(config_path))

    result = runner.invoke(app, ["Source text.", "--model", "missing"], color=False)

    assert result.exit_code != 0
    assert "Unknown model preset: missing" in result.output
