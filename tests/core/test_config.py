import json
from pathlib import Path

import pytest

from briefly_core.config import load_config, normalize_config, parse_config_text, resolve_config_path


def write_config(home: Path, value: object) -> Path:
    config_dir = home / ".briefly"
    config_dir.mkdir(parents=True)
    config_path = config_dir / "config.json"
    config_path.write_text(json.dumps(value), encoding="utf-8")
    return config_path


def test_resolves_default_config_path(tmp_path: Path) -> None:
    assert resolve_config_path({"HOME": str(tmp_path)}) == tmp_path / ".briefly" / "config.json"
    assert resolve_config_path({"USERPROFILE": str(tmp_path)}) == (
        tmp_path / ".briefly" / "config.json"
    )


def test_supports_explicit_config_path(tmp_path: Path) -> None:
    config_path = tmp_path / "custom.json"
    assert resolve_config_path({"BRIEFLY_CONFIG": str(config_path), "HOME": "ignored"}) == config_path


def test_returns_none_when_no_home_is_available() -> None:
    assert resolve_config_path({}) is None
    assert load_config({}) == load_config({"HOME": None, "USERPROFILE": None})


def test_loads_missing_config_as_none(tmp_path: Path) -> None:
    loaded = load_config({"HOME": str(tmp_path)})
    assert loaded.path == tmp_path / ".briefly" / "config.json"
    assert loaded.config is None


def test_loads_and_normalizes_config(tmp_path: Path) -> None:
    config_path = write_config(
        tmp_path,
        {
            "model": "auto",
            "output": {"language": " en ", "length": "long"},
            "cache": {"enabled": True, "maxMb": 256, "ttlDays": 14, "path": " cache.db "},
            "ui": {"theme": "moss"},
        },
    )

    loaded = load_config({"HOME": str(tmp_path)})

    assert loaded.path == config_path
    assert loaded.config == {
        "model": {"mode": "auto"},
        "output": {"language": "en", "length": "long"},
        "cache": {"enabled": True, "maxMb": 256, "ttlDays": 14, "path": "cache.db"},
        "ui": {"theme": "moss"},
    }


def test_normalizes_model_shorthand() -> None:
    assert normalize_config({"model": "auto"}) == {"model": {"mode": "auto"}}
    assert normalize_config({"model": "openai/gpt-5-mini"}) == {
        "model": {"id": "openai/gpt-5-mini"}
    }
    assert normalize_config({"model": "fast"}) == {"model": {"name": "fast"}}


def test_normalizes_named_models() -> None:
    assert normalize_config(
        {
            "model": "fast",
            "models": {
                "fast": "openai/gpt-5-mini",
                "local": {"id": "openai/local-model"},
            },
        }
    ) == {
        "model": {"name": "fast"},
        "models": {
            "fast": {"id": "openai/gpt-5-mini"},
            "local": {"id": "openai/local-model"},
        },
    }


def test_rejects_comments() -> None:
    with pytest.raises(ValueError, match="comments are not allowed"):
        parse_config_text('{\n// nope\n"model": "auto"\n}')

    with pytest.raises(ValueError, match="comments are not allowed"):
        parse_config_text('/* nope */\n{"model": "auto"}')


def test_allows_comment_markers_inside_strings() -> None:
    assert parse_config_text('{"url": "https://example.com/a//b"}') == {
        "url": "https://example.com/a//b"
    }


def test_rejects_invalid_json_and_top_level_arrays() -> None:
    with pytest.raises(ValueError, match="Invalid JSON"):
        parse_config_text("{")

    with pytest.raises(ValueError, match="expected an object"):
        parse_config_text("[]")


def test_rejects_invalid_model_values() -> None:
    with pytest.raises(ValueError, match="model must not be empty"):
        normalize_config({"model": "   "})

    with pytest.raises(ValueError, match="model must be a string or object"):
        normalize_config({"model": 42})

    with pytest.raises(ValueError, match='model must include "id"'):
        normalize_config({"model": {}})

    with pytest.raises(ValueError, match='model.mode must be "auto"'):
        normalize_config({"model": {"mode": "manual"}})


def test_rejects_invalid_sections() -> None:
    with pytest.raises(ValueError, match="output.length"):
        normalize_config({"output": {"length": 123}})

    with pytest.raises(ValueError, match="Unsupported --length"):
        normalize_config({"output": {"length": "1"}})

    with pytest.raises(ValueError, match="cache.enabled"):
        normalize_config({"cache": {"enabled": "yes"}})

    with pytest.raises(ValueError, match="ui.theme"):
        normalize_config({"ui": {"theme": 7}})


def test_rejects_reserved_auto_model_name() -> None:
    with pytest.raises(ValueError, match="reserved"):
        normalize_config({"models": {"auto": "openai/gpt-5-mini"}})

