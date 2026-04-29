from __future__ import annotations

from pathlib import Path

import pytest

from briefly_core.pdf import extract_pdf


def _make_test_pdf(pages: list[str], *, title: str | None = None) -> bytes:
    """Build a minimal valid PDF with one or more text-bearing pages.

    Pass an empty string for a blank page. Pass a title to inject /Info metadata.
    """
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

    trailer = (
        b"trailer\n"
        + trailer_dict
        + b"\nstartxref\n"
        + str(xref_offset).encode()
        + b"\n%%EOF\n"
    )

    return body + xref + trailer


def test_extract_pdf_returns_text(tmp_path: Path) -> None:
    pdf_path = tmp_path / "sample.pdf"
    pdf_path.write_bytes(_make_test_pdf(["Hello PDF World"]))

    result = extract_pdf(pdf_path)

    assert "Hello PDF World" in result.text
    assert result.source == str(pdf_path)


def test_extract_pdf_uses_metadata_title(tmp_path: Path) -> None:
    pdf_path = tmp_path / "titled.pdf"
    pdf_path.write_bytes(_make_test_pdf(["Body text here"], title="My Paper"))

    result = extract_pdf(pdf_path)

    assert result.title == "My Paper"


def test_extract_pdf_falls_back_to_filename_stem(tmp_path: Path) -> None:
    pdf_path = tmp_path / "research-notes.pdf"
    pdf_path.write_bytes(_make_test_pdf(["Some content"]))

    result = extract_pdf(pdf_path)

    assert result.title == "research-notes"


def test_extract_pdf_raises_on_empty_text(tmp_path: Path) -> None:
    pdf_path = tmp_path / "blank.pdf"
    pdf_path.write_bytes(_make_test_pdf([""]))

    with pytest.raises(ValueError, match="no extractable text"):
        extract_pdf(pdf_path)


def test_extract_pdf_joins_multiple_pages(tmp_path: Path) -> None:
    pdf_path = tmp_path / "combined.pdf"
    pdf_path.write_bytes(_make_test_pdf(["First page content", "Second page content"]))

    result = extract_pdf(pdf_path)

    assert "First page content" in result.text
    assert "Second page content" in result.text
