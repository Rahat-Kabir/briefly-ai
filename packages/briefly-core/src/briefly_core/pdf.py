from __future__ import annotations

from io import BytesIO
from pathlib import Path
import re
from typing import Any, Mapping

import pdfplumber

from briefly_core.content import ExtractedContent
from briefly_core.image import extract_text_via_vision

_WHITESPACE_PATTERN = re.compile(r"[ \t\r\f\v]+")
_BLANK_LINES_PATTERN = re.compile(r"\n{3,}")

_MIN_PDF_TEXT_CHARS = 50
PDF_VISION_PROMPT = (
    "Transcribe all text from this PDF document as plain text. "
    "Preserve reading order across pages. Do not add commentary."
)


def extract_pdf(path: Path) -> ExtractedContent:
    with pdfplumber.open(str(path)) as pdf:
        return _extract_open_pdf(pdf, source=str(path), title_hint=path.stem or None)


def extract_pdf_bytes(
    data: bytes,
    *,
    source: str,
    title_hint: str | None = None,
) -> ExtractedContent:
    with pdfplumber.open(BytesIO(data)) as pdf:
        content = _extract_open_pdf(pdf, source=source, title_hint=title_hint)
    if not content.text:
        raise ValueError(f"PDF contained no extractable text: {source}")
    return content


def has_extractable_pdf_text(content: ExtractedContent) -> bool:
    return _non_whitespace_count(content.text) >= _MIN_PDF_TEXT_CHARS


async def extract_pdf_via_vision(path: Path, model: str) -> ExtractedContent:
    text = await extract_text_via_vision(
        data=path.read_bytes(),
        mime="application/pdf",
        model=model,
        prompt=PDF_VISION_PROMPT,
        source=str(path),
        media_label="pdf",
    )
    return ExtractedContent(source=str(path), title=path.stem or None, text=text)


def _extract_open_pdf(
    pdf,
    *,
    source: str,
    title_hint: str | None,
) -> ExtractedContent:
    pages = [_clean_page_text(page.extract_text() or "") for page in pdf.pages]
    title = _pdf_title(pdf.metadata, title_hint=title_hint)
    text = _BLANK_LINES_PATTERN.sub("\n\n", "\n\n".join(part for part in pages if part)).strip()
    return ExtractedContent(source=source, title=title, text=text)


def _non_whitespace_count(text: str) -> int:
    return sum(1 for char in text if not char.isspace())


def _clean_page_text(text: str) -> str:
    lines = [_WHITESPACE_PATTERN.sub(" ", line).strip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line)


def _pdf_title(metadata: Mapping[str, Any] | None, *, title_hint: str | None) -> str | None:
    if metadata:
        raw_title = metadata.get("Title")
        if isinstance(raw_title, str):
            cleaned = _WHITESPACE_PATTERN.sub(" ", raw_title).strip()
            if cleaned:
                return cleaned
    return title_hint
