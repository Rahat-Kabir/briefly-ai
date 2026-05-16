from __future__ import annotations

import json
import os
from pathlib import Path

from click.testing import CliRunner
import pytest

from briefly_cli.main import app

runner = CliRunner()


def _write_image(directory: Path, name: str = "shot.png", content: bytes = b"img") -> Path:
    path = directory / name
    path.write_bytes(content)
    return path


class _ExtractCapture:
    def __init__(self) -> None:
        self.calls: int = 0
        self.models: list[str] = []


def _patch_extract(
    monkeypatch: pytest.MonkeyPatch,
    text: str = "OCR text from image.",
) -> _ExtractCapture:
    captured = _ExtractCapture()

    async def fake_extract(path: Path, model: str) -> str:
        captured.calls += 1
        captured.models.append(model)
        assert path.exists()
        return text

    monkeypatch.setattr(
        "briefly_cli.commands.brief.extract_text_from_image",
        fake_extract,
    )
    return captured


def test_extract_image_with_vision_model(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    image = _write_image(tmp_path)
    captured = _patch_extract(monkeypatch)

    result = runner.invoke(
        app,
        [str(image), "--extract", "--vision-model", "gemini/gemini-2.5-flash-lite"],
        color=False,
    )

    assert result.exit_code == 0, result.stdout
    assert result.stdout == "OCR text from image.\n"
    assert captured.models == ["gemini/gemini-2.5-flash-lite"]


def test_extract_image_json_payload(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    image = _write_image(tmp_path)
    _patch_extract(monkeypatch)

    result = runner.invoke(
        app,
        [
            str(image),
            "--extract",
            "--json",
            "--vision-model",
            "gemini/gemini-2.5-flash-lite",
        ],
        color=False,
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["input"]["kind"] == "image"
    assert payload["extracted"] == {
        "kind": "image",
        "source": str(image),
        "text": "OCR text from image.",
    }
    assert payload["summary"] is None


def test_briefing_image_uses_extract_then_brief(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    image = _write_image(tmp_path)
    _patch_extract(monkeypatch, text="The diagram shows a CPU connected to RAM.")

    captured_brief: dict[str, object] = {}

    async def fake_generate_brief(request):
        captured_brief["text"] = request.text
        captured_brief["kind"] = request.input_kind
        captured_brief["model"] = request.options.model
        return type(
            "Result",
            (),
            {"text": "BRIEF", "model": request.options.model},
        )()

    monkeypatch.setattr(
        "briefly_cli.commands.brief.generate_brief", fake_generate_brief
    )

    result = runner.invoke(
        app,
        [
            str(image),
            "--model",
            "openai/gpt-4o-mini",
            "--vision-model",
            "gemini/gemini-2.5-flash-lite",
            "--stream",
            "off",
        ],
        color=False,
    )

    assert result.exit_code == 0, result.stdout
    assert result.stdout.strip() == "BRIEF"
    assert captured_brief["text"] == "The diagram shows a CPU connected to RAM."
    assert captured_brief["kind"] == "image"
    assert captured_brief["model"] == "openai/gpt-4o-mini"


def test_image_extraction_uses_cache(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    image = _write_image(tmp_path)
    captured = _patch_extract(monkeypatch)

    first = runner.invoke(
        app,
        [str(image), "--extract", "--vision-model", "gemini/gemini-2.5-flash-lite"],
        color=False,
    )
    second = runner.invoke(
        app,
        [str(image), "--extract", "--vision-model", "gemini/gemini-2.5-flash-lite"],
        color=False,
    )

    assert first.exit_code == 0, first.stdout
    assert second.exit_code == 0, second.stdout
    assert captured.calls == 1
    assert first.stdout == second.stdout


def test_image_cache_invalidated_on_mtime_change(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    image = _write_image(tmp_path)
    captured = _ExtractCapture()

    async def fake_extract(_path: Path, _model: str) -> str:
        captured.calls += 1
        return f"OCR pass {captured.calls}."

    monkeypatch.setattr(
        "briefly_cli.commands.brief.extract_text_from_image", fake_extract
    )

    first = runner.invoke(
        app,
        [str(image), "--extract", "--vision-model", "gemini/gemini-2.5-flash-lite"],
        color=False,
    )
    assert first.exit_code == 0, first.stdout

    image.write_bytes(b"different bytes")
    new_time = image.stat().st_mtime + 5
    os.utime(image, (new_time, new_time))

    second = runner.invoke(
        app,
        [str(image), "--extract", "--vision-model", "gemini/gemini-2.5-flash-lite"],
        color=False,
    )
    assert second.exit_code == 0, second.stdout

    assert captured.calls == 2
    assert "OCR pass 2." in second.stdout


def test_image_skip_cache_recomputes(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    image = _write_image(tmp_path)
    captured = _patch_extract(monkeypatch)

    runner.invoke(
        app,
        [
            str(image),
            "--extract",
            "--skip-cache",
            "--vision-model",
            "gemini/gemini-2.5-flash-lite",
        ],
        color=False,
    )
    runner.invoke(
        app,
        [
            str(image),
            "--extract",
            "--skip-cache",
            "--vision-model",
            "gemini/gemini-2.5-flash-lite",
        ],
        color=False,
    )

    assert captured.calls == 2


def test_image_uses_config_vision_model(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    image = _write_image(tmp_path)
    captured = _patch_extract(monkeypatch)

    config_dir = tmp_path / ".briefly"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "config.json").write_text(
        json.dumps(
            {
                "model": "openai/gpt-4o-mini",
                "vision": {"model": "gemini/gemini-2.5-flash-lite"},
            }
        ),
        encoding="utf-8",
    )

    result = runner.invoke(app, [str(image), "--extract"], color=False)

    assert result.exit_code == 0, result.stdout
    assert captured.models == ["gemini/gemini-2.5-flash-lite"]


def test_image_falls_back_to_default_model(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    image = _write_image(tmp_path)
    captured = _patch_extract(monkeypatch)

    config_dir = tmp_path / ".briefly"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "config.json").write_text(
        json.dumps({"model": "gemini/gemini-2.5-flash-lite"}),
        encoding="utf-8",
    )

    result = runner.invoke(app, [str(image), "--extract"], color=False)

    assert result.exit_code == 0, result.stdout
    assert captured.models == ["gemini/gemini-2.5-flash-lite"]


def test_image_without_vision_model_errors(tmp_path: Path) -> None:
    image = _write_image(tmp_path)

    result = runner.invoke(app, [str(image), "--extract"], color=False)

    assert result.exit_code != 0
    assert "vision-capable model" in result.stderr
