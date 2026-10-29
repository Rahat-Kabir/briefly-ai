from __future__ import annotations

import codecs
from dataclasses import dataclass
from pathlib import Path
import re
from typing import Callable, Literal
from urllib.parse import urlparse

from briefly_core.audio import is_supported_audio_path, is_supported_video_path
from briefly_core.image import is_supported_image_path

InputKind = Literal["text", "file", "stdin", "url", "pdf", "audio", "video", "image"]

_FILE_EXTENSION_PATTERN = re.compile(r"\.[A-Za-z][A-Za-z0-9]{0,4}$")


@dataclass(frozen=True)
class ResolvedInput:
    kind: InputKind
    source: str
    text: str | None


def resolve_input_target(
    raw_input: str,
    *,
    stdin_reader: Callable[[], str] | None = None,
) -> ResolvedInput:
    if raw_input == "-":
        if stdin_reader is None:
            raise ValueError("stdin input requires a reader")
        return ResolvedInput(kind="stdin", source="-", text=stdin_reader())

    if _is_http_url(raw_input):
        return ResolvedInput(kind="url", source=raw_input, text=None)

    path = Path(raw_input).expanduser()
    if path.exists() and path.is_file():
        if path.suffix.lower() == ".pdf":
            return ResolvedInput(kind="pdf", source=str(path), text=None)
        if is_supported_audio_path(path):
            return ResolvedInput(kind="audio", source=str(path), text=None)
        if is_supported_video_path(path):
            return ResolvedInput(kind="video", source=str(path), text=None)
        if is_supported_image_path(path):
            return ResolvedInput(kind="image", source=str(path), text=None)
        return ResolvedInput(kind="file", source=str(path), text=_read_text_file(path))

    if path.is_dir():
        raise ValueError(
            f"Input is a folder, not a file: {raw_input}. Pass a file inside it, or "
            f'to brief it as literal text, pipe it: echo "{raw_input}" | briefly -'
        )

    if _looks_like_file_path(raw_input):
        raise ValueError(
            f"File not found: {raw_input}. "
            f'To brief it as literal text, pipe it: echo "{raw_input}" | briefly -'
        )

    return ResolvedInput(kind="text", source="literal", text=raw_input)


def _looks_like_file_path(raw_input: str) -> bool:
    # A sentence that mentions a file ("Read notes.md") has spaces but no path
    # separator, so it stays text.
    if "\n" in raw_input or not _FILE_EXTENSION_PATTERN.search(raw_input):
        return False
    has_separator = "/" in raw_input or "\\" in raw_input
    return has_separator or " " not in raw_input


def _read_text_file(path: Path) -> str:
    # UTF-16 is only detected by its BOM; Windows PowerShell 5.1 `>` writes UTF-16 LE with one.
    with path.open("rb") as file:
        head = file.read(2)
    encoding = "utf-16" if head in (codecs.BOM_UTF16_LE, codecs.BOM_UTF16_BE) else "utf-8-sig"
    try:
        return path.read_text(encoding=encoding)
    except UnicodeDecodeError as error:
        raise ValueError(
            f"File is not UTF-8 or UTF-16 text: {path}. "
            "Save it as UTF-8 or use a supported file type."
        ) from error


def _is_http_url(raw_input: str) -> bool:
    parsed = urlparse(raw_input)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)
