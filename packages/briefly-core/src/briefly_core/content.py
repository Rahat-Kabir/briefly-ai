from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
import re
from typing import Literal
from urllib.parse import unquote

import httpx
from bs4 import BeautifulSoup
from markdownify import ATX, markdownify
from trafilatura import extract as trafilatura_extract
from trafilatura import extract_metadata

Fetcher = Callable[[str], Awaitable[httpx.Response]]
ContentFormat = Literal["text", "markdown"]

_DEFAULT_TIMEOUT_SECONDS = 15.0
_WHITESPACE_PATTERN = re.compile(r"[ \t\r\f\v]+")
_BLANK_LINES_PATTERN = re.compile(r"\n{3,}")


@dataclass(frozen=True)
class ExtractedContent:
    source: str
    title: str | None
    text: str


async def extract_url(
    url: str,
    *,
    output_format: ContentFormat = "text",
    fetcher: Fetcher | None = None,
) -> ExtractedContent:
    response = await _fetch_url(url, fetcher)
    content_type = response.headers.get("content-type", "")
    if _is_pdf_response(response, content_type):
        from briefly_core.pdf import extract_pdf_bytes

        return extract_pdf_bytes(
            response.content,
            source=str(response.url),
            title_hint=_title_hint_from_url(str(response.url)),
        )

    if "text/html" not in content_type.lower():
        raise ValueError(f"URL did not return HTML content: {content_type or 'unknown'}")

    html = response.text
    title, text = extract_html_text(html, output_format=output_format)
    if not text:
        raise ValueError("URL did not contain extractable text.")

    return ExtractedContent(source=str(response.url), title=title, text=text)


def _is_pdf_response(response: httpx.Response, content_type: str) -> bool:
    normalized_type = content_type.lower()
    if "application/pdf" in normalized_type:
        return True
    return str(response.url.path).lower().endswith(".pdf")


def _title_hint_from_url(url: str) -> str | None:
    path = httpx.URL(url).path
    name = unquote(path.rsplit("/", 1)[-1])
    if not name:
        return None
    stem = name.rsplit(".", 1)[0] if "." in name else name
    cleaned = _clean_inline_text(stem.replace("-", " ").replace("_", " "))
    return cleaned


def extract_html_text(html: str, *, output_format: ContentFormat = "text") -> tuple[str | None, str]:
    title = _extract_html_title(html) or _extract_trafilatura_title(html)
    cleaned_html = _remove_non_content_elements(html)
    text = _extract_trafilatura_text(cleaned_html, output_format=output_format)
    if text:
        return title, text

    fallback_title, fallback_text = _extract_html_text_fallback(
        cleaned_html,
        output_format=output_format,
    )
    return title or fallback_title, fallback_text


def _extract_trafilatura_text(html: str, *, output_format: ContentFormat = "text") -> str:
    kwargs: dict[str, object] = {"include_comments": False}
    if output_format == "markdown":
        kwargs["output_format"] = "markdown"

    text = trafilatura_extract(html, **kwargs)
    if not isinstance(text, str):
        return ""
    return _clean_block_text(text)


def _extract_trafilatura_title(html: str) -> str | None:
    metadata = extract_metadata(html)
    title = getattr(metadata, "title", None) if metadata else None
    if not isinstance(title, str):
        return None
    return _clean_inline_text(title)


def _extract_html_title(html: str) -> str | None:
    soup = BeautifulSoup(html, "html.parser")
    return _clean_inline_text(soup.title.get_text(" ", strip=True)) if soup.title else None


def _remove_non_content_elements(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for element in soup(["script", "style", "noscript"]):
        element.decompose()
    return str(soup)


def _extract_html_text_fallback(
    html: str,
    *,
    output_format: ContentFormat = "text",
) -> tuple[str | None, str]:
    soup = BeautifulSoup(html, "html.parser")

    title = _clean_inline_text(soup.title.get_text(" ", strip=True)) if soup.title else None
    for element in soup(["head", "title", "meta", "link"]):
        element.decompose()

    body = soup.body or soup
    if output_format == "markdown":
        text = _clean_block_text(markdownify(str(body), heading_style=ATX))
    else:
        text = _clean_block_text(body.get_text("\n", strip=True))
    return title, text


async def _fetch_url(url: str, fetcher: Fetcher | None) -> httpx.Response:
    if fetcher is not None:
        response = await fetcher(url)
    else:
        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=_DEFAULT_TIMEOUT_SECONDS,
        ) as client:
            response = await client.get(url)

    response.raise_for_status()
    return response


def _clean_inline_text(text: str) -> str | None:
    normalized = _WHITESPACE_PATTERN.sub(" ", text).strip()
    return normalized or None


def _clean_block_text(text: str) -> str:
    lines = [_WHITESPACE_PATTERN.sub(" ", line).strip() for line in text.splitlines()]
    normalized = "\n".join(line for line in lines if line)
    return _BLANK_LINES_PATTERN.sub("\n\n", normalized).strip()
