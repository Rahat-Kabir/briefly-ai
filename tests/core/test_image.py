from __future__ import annotations

import asyncio
import base64
from pathlib import Path
from typing import Any

import pytest

from briefly_core.image import (
    VISION_EXTRACTION_PROMPT,
    extract_text_from_image,
    image_content_type,
    is_supported_image_path,
    validate_local_image_file,
)


def test_image_extension_detection() -> None:
    assert is_supported_image_path(Path("screenshot.png"))
    assert is_supported_image_path(Path("photo.JPG"))
    assert is_supported_image_path(Path("note.jpeg"))
    assert is_supported_image_path(Path("frame.webp"))
    assert is_supported_image_path(Path("sticker.gif"))
    assert not is_supported_image_path(Path("notes.txt"))
    assert not is_supported_image_path(Path("paper.pdf"))


def test_image_content_type() -> None:
    assert image_content_type(Path("a.png")) == "image/png"
    assert image_content_type(Path("a.jpg")) == "image/jpeg"
    assert image_content_type(Path("a.jpeg")) == "image/jpeg"
    assert image_content_type(Path("a.webp")) == "image/webp"
    assert image_content_type(Path("a.gif")) == "image/gif"
    assert image_content_type(Path("a.bin")) == "application/octet-stream"


def test_validate_local_image_rejects_unsupported(tmp_path: Path) -> None:
    path = tmp_path / "doc.txt"
    path.write_text("hello", encoding="utf-8")
    with pytest.raises(ValueError, match="Unsupported image file type"):
        validate_local_image_file(path)


def test_validate_local_image_rejects_missing(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="Image file does not exist"):
        validate_local_image_file(tmp_path / "missing.png")


def test_extract_text_from_image_calls_litellm_with_vision_message(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    path = tmp_path / "shot.png"
    image_bytes = b"\x89PNG\r\n\x1a\nfake-image-bytes"
    path.write_bytes(image_bytes)

    captured: dict[str, Any] = {}

    async def fake_acompletion(**kwargs: Any) -> Any:
        captured.update(kwargs)
        return {
            "choices": [
                {"message": {"content": " Extracted text. "}}
            ]
        }

    import litellm

    monkeypatch.setattr(litellm, "acompletion", fake_acompletion)

    async def run() -> str:
        return await extract_text_from_image(path, "gemini/gemini-2.5-flash-lite")

    result = asyncio.run(run())

    assert result == "Extracted text."
    assert captured["model"] == "gemini/gemini-2.5-flash-lite"
    messages = captured["messages"]
    assert len(messages) == 1
    content = messages[0]["content"]
    assert content[0] == {"type": "text", "text": VISION_EXTRACTION_PROMPT}
    image_part = content[1]
    assert image_part["type"] == "image_url"
    expected_b64 = base64.b64encode(image_bytes).decode("ascii")
    assert image_part["image_url"]["url"] == f"data:image/png;base64,{expected_b64}"


def test_extract_text_from_image_wraps_litellm_errors(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    path = tmp_path / "shot.png"
    path.write_bytes(b"img")

    async def fake_acompletion(**_: Any) -> Any:
        raise RuntimeError("model does not support image input")

    import litellm

    monkeypatch.setattr(litellm, "acompletion", fake_acompletion)

    async def run() -> None:
        with pytest.raises(RuntimeError, match="vision.model"):
            await extract_text_from_image(path, "openai/gpt-4o-mini-text-only")

    asyncio.run(run())


def test_extract_text_from_image_rejects_empty_response(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    path = tmp_path / "shot.png"
    path.write_bytes(b"img")

    async def fake_acompletion(**_: Any) -> Any:
        return {"choices": [{"message": {"content": "   "}}]}

    import litellm

    monkeypatch.setattr(litellm, "acompletion", fake_acompletion)

    async def run() -> None:
        with pytest.raises(RuntimeError, match="empty text"):
            await extract_text_from_image(path, "gemini/gemini-2.5-flash-lite")

    asyncio.run(run())


def test_extract_text_from_image_requires_model(tmp_path: Path) -> None:
    path = tmp_path / "shot.png"
    path.write_bytes(b"img")

    async def run() -> None:
        with pytest.raises(ValueError, match="vision-capable model"):
            await extract_text_from_image(path, "")

    asyncio.run(run())
