import asyncio

import httpx
import pytest

from briefly_core.content import extract_html_text, extract_url


def test_extract_html_text_removes_non_content_elements() -> None:
    title, text = extract_html_text(
        """
        <html>
          <head>
            <title> Example Page </title>
            <style>.hidden { display: none; }</style>
            <script>console.log("ignore")</script>
          </head>
          <body>
            <h1>Main heading</h1>
            <p>First paragraph.</p>
            <noscript>ignore this</noscript>
            <p>Second paragraph.</p>
          </body>
        </html>
        """
    )

    assert title == "Example Page"
    assert "Main heading" in text
    assert "First paragraph." in text
    assert "Second paragraph." in text
    assert "console.log" not in text
    assert "ignore this" not in text


def test_extract_html_text_uses_trafilatura_first(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "briefly_core.content._extract_trafilatura_text",
        lambda html, **kwargs: "Main article text.",
    )
    monkeypatch.setattr(
        "briefly_core.content._extract_trafilatura_title",
        lambda html: "Article Title",
    )

    title, text = extract_html_text("<article>Article text.</article>")

    assert title == "Article Title"
    assert text == "Main article text."


def test_extract_html_text_falls_back_when_trafilatura_is_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("briefly_core.content._extract_trafilatura_text", lambda html, **kwargs: "")
    monkeypatch.setattr("briefly_core.content._extract_trafilatura_title", lambda html: None)

    title, text = extract_html_text(
        "<title>Fallback Title</title><main><p>Fallback text.</p></main>"
    )

    assert title == "Fallback Title"
    assert text == "Fallback text."


def test_extract_html_text_can_return_markdown(monkeypatch: pytest.MonkeyPatch) -> None:
    seen_format = None

    def fake_trafilatura_text(html: str, **kwargs):
        nonlocal seen_format
        seen_format = kwargs["output_format"]
        return "# Article\n\n[Link](https://example.com)"

    monkeypatch.setattr(
        "briefly_core.content._extract_trafilatura_text",
        fake_trafilatura_text,
    )

    title, text = extract_html_text("<title>Article</title>", output_format="markdown")

    assert seen_format == "markdown"
    assert title == "Article"
    assert text == "# Article\n\n[Link](https://example.com)"


def test_extract_html_text_markdown_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("briefly_core.content._extract_trafilatura_text", lambda html, **kwargs: "")
    monkeypatch.setattr("briefly_core.content._extract_trafilatura_title", lambda html: None)

    title, text = extract_html_text(
        '<title>Fallback Title</title><main><h1>Heading</h1><p>A <a href="/x">link</a>.</p></main>',
        output_format="markdown",
    )

    assert title == "Fallback Title"
    assert "# Heading" in text
    assert "[link](/x)" in text


def test_extract_url_uses_fetcher_and_returns_content() -> None:
    async def fetcher(url: str) -> httpx.Response:
        request = httpx.Request("GET", url)
        return httpx.Response(
            200,
            headers={"content-type": "text/html; charset=utf-8"},
            text="<title>Example</title><main><p>Hello from the page.</p></main>",
            request=request,
        )

    result = asyncio.run(extract_url("https://example.com", fetcher=fetcher))

    assert result.source == "https://example.com"
    assert result.title == "Example"
    assert result.text == "Hello from the page."


def test_extract_url_rejects_non_html_content() -> None:
    async def fetcher(url: str) -> httpx.Response:
        request = httpx.Request("GET", url)
        return httpx.Response(
            200,
            headers={"content-type": "application/json"},
            text='{"ok": true}',
            request=request,
        )

    with pytest.raises(ValueError, match="did not return HTML"):
        asyncio.run(extract_url("https://example.com/data.json", fetcher=fetcher))


def test_extract_url_rejects_empty_pages() -> None:
    async def fetcher(url: str) -> httpx.Response:
        request = httpx.Request("GET", url)
        return httpx.Response(
            200,
            headers={"content-type": "text/html"},
            text="<html><head><title>Empty</title></head><body></body></html>",
            request=request,
        )

    with pytest.raises(ValueError, match="extractable text"):
        asyncio.run(extract_url("https://example.com/empty", fetcher=fetcher))
