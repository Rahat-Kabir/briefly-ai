from __future__ import annotations

from pathlib import Path
import re
from typing import Any, Mapping

import pdfplumber

from briefly_core.content import ExtractedContent

_WHITESPACE_PATTERN = re.compile(r"[ \t\r\f\v]+")
_BLANK_LINES_PATTERN = re.compile(r"\n{3,}")


def extract_pdf(path: Path) -> ExtractedContent:
    with pdfplumber.open(str(path)) as pdf:
        pages = [_clean_page_text(page.extract_text() or "") for page in pdf.pages]
        title = _pdf_title(pdf.metadata, path)

    text = _BLANK_LINES_PATTERN.sub("\n\n", "\n\n".join(part for part in pages if part)).strip()
    if not text:
        raise ValueError(f"PDF contained no extractable text: {path}")

    return ExtractedContent(source=str(path), title=title, text=text)


def _clean_page_text(text: str) -> str:
    lines = [_WHITESPACE_PATTERN.sub(" ", line).strip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line)


def _pdf_title(metadata: Mapping[str, Any] | None, path: Path) -> str | None:
    if metadata:
        raw_title = metadata.get("Title")
        if isinstance(raw_title, str):
            cleaned = _WHITESPACE_PATTERN.sub(" ", raw_title).strip()
            if cleaned:
                return cleaned
    return path.stem or None
