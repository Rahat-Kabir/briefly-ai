from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
import re

import httpx
from bs4 import BeautifulSoup

Fetcher = Callable[[str], Awaitable[httpx.Response]]

_DEFAULT_TIMEOUT_SECONDS = 15.0
_WHITESPACE_PATTERN = re.compile(r"[ \t\r\f\v]+")
_BLANK_LINES_PATTERN = re.compile(r"\n{3,}")


@dataclass(frozen=True)
class ExtractedContent:
    source: str
    title: str | None
    text: str


async def extract_url(url: str, *, fetcher: Fetcher | None = None) -> ExtractedContent:
    response = await _fetch_url(url, fetcher)
    content_type = response.headers.get("content-type", "")
    if "text/html" not in content_type.lower():
        raise ValueError(f"URL did not return HTML content: {content_type or 'unknown'}")

    html = response.text
    title, text = extract_html_text(html)
    if not text:
        raise ValueError("URL did not contain extractable text.")

    return ExtractedContent(source=str(response.url), title=title, text=text)


def extract_html_text(html: str) -> tuple[str | None, str]:
    soup = BeautifulSoup(html, "html.parser")

    title = _clean_inline_text(soup.title.get_text(" ", strip=True)) if soup.title else None
    for element in soup(["script", "style", "noscript"]):
        element.decompose()
    for element in soup(["head", "title", "meta", "link"]):
        element.decompose()

    body = soup.body or soup
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
