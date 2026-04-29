import asyncio

import httpx
import pytest

from briefly_core.content import extract_html_text, extract_url


def _make_test_pdf(pages: list[str], *, title: str | None = None) -> bytes:
    objects: list[bytes] = []
    page_count = len(pages)
    page_obj_ids = [4 + 2 * i for i in range(page_count)]
    contents_obj_ids = [5 + 2 * i for i in range(page_count)]

    objects.append(b"<</Type/Catalog/Pages 2 0 R>>")
    kids = b" ".join(f"{pid} 0 R".encode() for pid in page_obj_ids)
    objects.append(
        b"<</Type/Pages/Kids[" + kids + b"]/Count " + str(page_count).encode() + b">>"
    )
    objects.append(b"<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>")

    for index, text in enumerate(pages):
        contents_id = contents_obj_ids[index]
        objects.append(
            (
                f"<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]"
                f"/Contents {contents_id} 0 R/Resources<</Font<</F1 3 0 R>>>>>>"
            ).encode()
        )
        if text:
            escaped = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
            stream = (
                b"BT /F1 12 Tf 72 720 Td ("
                + escaped.encode("latin-1", errors="replace")
                + b") Tj ET"
            )
        else:
            stream = b"q Q"
        objects.append(
            b"<</Length "
            + str(len(stream)).encode()
            + b">>\nstream\n"
            + stream
            + b"\nendstream"
        )

    info_id: int | None = None
    if title is not None:
        info_id = len(objects) + 1
        escaped_title = title.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        objects.append(
            b"<</Title (" + escaped_title.encode("latin-1", errors="replace") + b")>>"
        )

    body = b"%PDF-1.4\n"
    offsets: list[int] = []
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(body))
        body += f"{index} 0 obj\n".encode() + obj + b"\nendobj\n"

    xref_offset = len(body)
    xref = b"xref\n0 " + str(len(objects) + 1).encode() + b"\n"
    xref += b"0000000000 65535 f \n"
    for offset in offsets:
        xref += f"{offset:010d} 00000 n \n".encode()

    trailer_dict = b"<</Size " + str(len(objects) + 1).encode() + b"/Root 1 0 R"
    if info_id is not None:
        trailer_dict += b"/Info " + str(info_id).encode() + b" 0 R"
    trailer_dict += b">>"

    return (
        body
        + xref
        + b"trailer\n"
        + trailer_dict
        + b"\nstartxref\n"
        + str(xref_offset).encode()
        + b"\n%%EOF\n"
    )


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


def test_extract_url_extracts_pdf_content_type() -> None:
    async def fetcher(url: str) -> httpx.Response:
        request = httpx.Request("GET", url)
        return httpx.Response(
            200,
            headers={"content-type": "application/pdf"},
            content=_make_test_pdf(["Remote PDF body"], title="Remote Paper"),
            request=request,
        )

    result = asyncio.run(extract_url("https://example.com/paper", fetcher=fetcher))

    assert result.source == "https://example.com/paper"
    assert result.title == "Remote Paper"
    assert "Remote PDF body" in result.text


def test_extract_url_extracts_pdf_extension_with_generic_content_type() -> None:
    async def fetcher(url: str) -> httpx.Response:
        request = httpx.Request("GET", url)
        return httpx.Response(
            200,
            headers={"content-type": "application/octet-stream"},
            content=_make_test_pdf(["Generic PDF body"]),
            request=request,
        )

    result = asyncio.run(extract_url("https://example.com/research-notes.pdf", fetcher=fetcher))

    assert result.title == "research notes"
    assert "Generic PDF body" in result.text


def test_extract_url_rejects_pdf_with_no_text() -> None:
    async def fetcher(url: str) -> httpx.Response:
        request = httpx.Request("GET", url)
        return httpx.Response(
            200,
            headers={"content-type": "application/pdf"},
            content=_make_test_pdf([""]),
            request=request,
        )

    with pytest.raises(ValueError, match="PDF contained no extractable text"):
        asyncio.run(extract_url("https://example.com/scan.pdf", fetcher=fetcher))


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
