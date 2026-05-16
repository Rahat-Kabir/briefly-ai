from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
from typing import Any, Mapping

from briefly_core.flags import parse_length_arg

ConfigData = dict[str, Any]


@dataclass(frozen=True)
class LoadedConfig:
    path: Path | None
    config: ConfigData | None


def load_config(env: Mapping[str, str | None] | None = None) -> LoadedConfig:
    config_path = resolve_config_path(env)
    if config_path is None:
        return LoadedConfig(path=None, config=None)

    if not config_path.exists():
        return LoadedConfig(path=config_path, config=None)

    raw = config_path.read_text(encoding="utf-8")
    parsed = parse_config_text(raw, config_path)
    return LoadedConfig(path=config_path, config=normalize_config(parsed))


def resolve_config_path(env: Mapping[str, str | None] | None = None) -> Path | None:
    values = os.environ if env is None else env

    explicit_path = _clean_string(values.get("BRIEFLY_CONFIG"))
    if explicit_path:
        return Path(explicit_path).expanduser()

    home = _clean_string(values.get("HOME")) or _clean_string(values.get("USERPROFILE"))
    if not home:
        return None

    return Path(home).expanduser() / ".briefly" / "config.json"


def parse_config_text(raw: str, path: str | Path = "config.json") -> ConfigData:
    _reject_json_comments(raw, str(path))
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as error:
        raise ValueError(f"Invalid JSON in config file {path}: {error.msg}") from error

    if not isinstance(parsed, dict):
        raise ValueError(f"Invalid config file {path}: expected an object at the top level")

    return parsed


def normalize_config(raw: Mapping[str, Any]) -> ConfigData:
    config = dict(raw)

    if "model" in config:
        config["model"] = _normalize_model(config["model"], "model")

    if "models" in config:
        config["models"] = _normalize_models(config["models"])

    if "output" in config:
        config["output"] = _normalize_output(config["output"])

    if "cache" in config:
        config["cache"] = _normalize_cache(config["cache"])

    if "ui" in config:
        config["ui"] = _normalize_ui(config["ui"])

    if "vision" in config:
        config["vision"] = _normalize_vision(config["vision"])

    return config


def _normalize_vision(raw: Any) -> ConfigData:
    if isinstance(raw, str):
        return _normalize_model(raw, "vision.model")
    if not isinstance(raw, dict):
        raise ValueError("vision must be a string or object")

    vision: ConfigData = {}
    if "model" in raw:
        vision = _normalize_model(raw["model"], "vision.model")
    return vision


def _normalize_model(raw: Any, label: str) -> ConfigData:
    if isinstance(raw, str):
        value = raw.strip()
        if not value:
            raise ValueError(f"{label} must not be empty")
        if value == "auto":
            return {"mode": "auto"}
        if "/" in value:
            return {"id": value}
        return {"name": value}

    if not isinstance(raw, dict):
        raise ValueError(f"{label} must be a string or object")

    model = dict(raw)
    id_value = _optional_clean_string(model.get("id"), f"{label}.id")
    name_value = _optional_clean_string(model.get("name"), f"{label}.name")
    mode_value = _optional_clean_string(model.get("mode"), f"{label}.mode")

    normalized: ConfigData = {}
    if id_value:
        normalized["id"] = id_value
    if name_value:
        normalized["name"] = name_value
    if mode_value:
        if mode_value != "auto":
            raise ValueError(f'{label}.mode must be "auto"')
        normalized["mode"] = mode_value

    if not normalized:
        raise ValueError(f'{label} must include "id", "name", or mode "auto"')

    if "rules" in model:
        normalized["rules"] = model["rules"]

    return normalized


def _normalize_models(raw: Any) -> ConfigData:
    if not isinstance(raw, dict):
        raise ValueError("models must be an object")

    models: ConfigData = {}
    for name, value in raw.items():
        if not isinstance(name, str) or not name.strip():
            raise ValueError("model names must be non-empty strings")
        normalized_name = name.strip()
        if normalized_name == "auto":
            raise ValueError('model name "auto" is reserved')
        models[normalized_name] = _normalize_model(value, f"models.{normalized_name}")
    return models


def _normalize_output(raw: Any) -> ConfigData:
    if not isinstance(raw, dict):
        raise ValueError("output must be an object")

    output: ConfigData = {}
    language = _optional_clean_string(raw.get("language"), "output.language")
    length = _optional_clean_string(raw.get("length"), "output.length")

    if language:
        output["language"] = language
    if length:
        parse_length_arg(length)
        output["length"] = length

    return output


def _normalize_cache(raw: Any) -> ConfigData:
    if not isinstance(raw, dict):
        raise ValueError("cache must be an object")

    cache: ConfigData = {}
    if "enabled" in raw:
        if not isinstance(raw["enabled"], bool):
            raise ValueError("cache.enabled must be a boolean")
        cache["enabled"] = raw["enabled"]

    for key in ("maxMb", "ttlDays"):
        if key not in raw:
            continue
        value = raw[key]
        if not isinstance(value, int | float) or isinstance(value, bool) or value <= 0:
            raise ValueError(f"cache.{key} must be a positive number")
        cache[key] = value

    path = _optional_clean_string(raw.get("path"), "cache.path")
    if path:
        cache["path"] = path

    return cache


def _normalize_ui(raw: Any) -> ConfigData:
    if not isinstance(raw, dict):
        raise ValueError("ui must be an object")

    ui: ConfigData = {}
    theme = _optional_clean_string(raw.get("theme"), "ui.theme")
    if theme:
        ui["theme"] = theme
    return ui


def _optional_clean_string(raw: Any, label: str) -> str | None:
    if raw is None:
        return None
    if not isinstance(raw, str):
        raise ValueError(f"{label} must be a string")
    value = raw.strip()
    return value or None


def _clean_string(raw: str | None) -> str | None:
    if raw is None:
        return None
    value = raw.strip()
    return value or None


def _reject_json_comments(raw: str, path: str) -> None:
    in_string: str | None = None
    escaped = False
    line = 1
    column = 1

    for index, char in enumerate(raw):
        next_char = raw[index + 1] if index + 1 < len(raw) else ""

        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == in_string:
                in_string = None
            line, column = _advance_position(char, line, column)
            continue

        if char in {'"', "'"}:
            in_string = char
            line, column = _advance_position(char, line, column)
            continue

        if char == "/" and next_char == "/":
            raise ValueError(
                f"Invalid config file {path}: comments are not allowed "
                f"(found // at {line}:{column})."
            )

        if char == "/" and next_char == "*":
            raise ValueError(
                f"Invalid config file {path}: comments are not allowed "
                f"(found /* at {line}:{column})."
            )

        line, column = _advance_position(char, line, column)


def _advance_position(char: str, line: int, column: int) -> tuple[int, int]:
    if char == "\n":
        return line + 1, 1
    return line, column + 1

