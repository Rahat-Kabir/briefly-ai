from __future__ import annotations

import base64
from pathlib import Path
from typing import Any

_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}

VISION_EXTRACTION_PROMPT = (
    "Transcribe everything visible in this image as plain text. "
    "Preserve reading order. Do not add commentary."
)


def is_supported_image_path(path: Path) -> bool:
    return path.suffix.lower() in _IMAGE_EXTENSIONS


def image_content_type(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".png":
        return "image/png"
    if suffix in {".jpg", ".jpeg"}:
        return "image/jpeg"
    if suffix == ".webp":
        return "image/webp"
    if suffix == ".gif":
        return "image/gif"
    return "application/octet-stream"


def validate_local_image_file(path: Path) -> None:
    if not path.exists() or not path.is_file():
        raise ValueError(f"Image file does not exist: {path}")
    if not is_supported_image_path(path):
        supported = ", ".join(sorted(_IMAGE_EXTENSIONS))
        raise ValueError(
            f"Unsupported image file type: {path.suffix}. Supported: {supported}"
        )


async def extract_text_from_image(path: Path, model: str) -> str:
    validate_local_image_file(path)
    if not model:
        raise ValueError(
            "A vision-capable model is required to read images. "
            "Set vision.model in ~/.briefly/config.json or pass --vision-model."
        )

    import litellm

    data_url = _build_data_url(path)
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": VISION_EXTRACTION_PROMPT},
                {"type": "image_url", "image_url": {"url": data_url}},
            ],
        }
    ]

    try:
        response = await litellm.acompletion(model=model, messages=messages)
    except Exception as error:
        raise RuntimeError(
            f"Image extraction failed with model '{model}': {error}. "
            "If this model does not support image input, set vision.model in "
            "~/.briefly/config.json to a vision-capable model (for example "
            "gemini/gemini-2.5-flash-lite) or pass --vision-model."
        ) from error

    text = _response_text(response)
    cleaned = text.strip()
    if not cleaned:
        raise RuntimeError(
            f"Vision model '{model}' returned empty text for image: {path}"
        )
    return cleaned


def _build_data_url(path: Path) -> str:
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{image_content_type(path)};base64,{encoded}"


def _response_text(response: Any) -> str:
    choices = _get_value(response, "choices")
    if not choices:
        raise RuntimeError("Vision model response did not include choices.")

    message = _get_value(choices[0], "message")
    content = _get_value(message, "content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for part in content:
            text_part = _get_value(part, "text")
            if isinstance(text_part, str):
                parts.append(text_part)
        if parts:
            return "".join(parts)
    raise RuntimeError("Vision model response did not include text content.")


def _get_value(value: Any, key: str) -> Any:
    if isinstance(value, dict):
        return value.get(key)
    return getattr(value, key, None)
