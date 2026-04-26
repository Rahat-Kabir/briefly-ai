import json
from pathlib import Path

from click.testing import CliRunner

from briefly_cli.main import app

runner = CliRunner()


def test_config_init_creates_config(monkeypatch, tmp_path: Path) -> None:
    config_path = tmp_path / "nested" / "config.json"
    monkeypatch.setenv("BRIEFLY_CONFIG", str(config_path))

    result = runner.invoke(
        app,
        ["config", "init", "--model", "openai/gpt-4o-mini"],
        color=False,
    )

    assert result.exit_code == 0
    assert f"Wrote config: {config_path}" in result.output
    assert json.loads(config_path.read_text(encoding="utf-8")) == {
        "model": "openai/gpt-4o-mini"
    }


def test_config_init_refuses_existing_config(monkeypatch, tmp_path: Path) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text('{"model": "existing/model"}\n', encoding="utf-8")
    monkeypatch.setenv("BRIEFLY_CONFIG", str(config_path))

    result = runner.invoke(
        app,
        ["config", "init", "--model", "openai/gpt-4o-mini"],
        color=False,
    )

    assert result.exit_code != 0
    assert f"Config already exists: {config_path}" in result.output
    assert json.loads(config_path.read_text(encoding="utf-8")) == {"model": "existing/model"}


def test_config_init_force_overwrites_existing_config(monkeypatch, tmp_path: Path) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text('{"model": "existing/model"}\n', encoding="utf-8")
    monkeypatch.setenv("BRIEFLY_CONFIG", str(config_path))

    result = runner.invoke(
        app,
        ["config", "init", "--model", "openai/gpt-4o-mini", "--force"],
        color=False,
    )

    assert result.exit_code == 0
    assert json.loads(config_path.read_text(encoding="utf-8")) == {
        "model": "openai/gpt-4o-mini"
    }


def test_config_init_requires_raw_model_id(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("BRIEFLY_CONFIG", str(tmp_path / "config.json"))

    result = runner.invoke(app, ["config", "init", "--model", "fast"], color=False)

    assert result.exit_code != 0
    assert "Model must be a raw model id" in result.output


def test_config_init_requires_resolvable_config_path(monkeypatch) -> None:
    monkeypatch.delenv("BRIEFLY_CONFIG", raising=False)
    monkeypatch.delenv("HOME", raising=False)
    monkeypatch.delenv("USERPROFILE", raising=False)

    result = runner.invoke(
        app,
        ["config", "init", "--model", "openai/gpt-4o-mini"],
        color=False,
        env={"BRIEFLY_CONFIG": "", "HOME": "", "USERPROFILE": ""},
    )

    assert result.exit_code != 0
    assert "Could not resolve config path. Set BRIEFLY_CONFIG." in result.output
