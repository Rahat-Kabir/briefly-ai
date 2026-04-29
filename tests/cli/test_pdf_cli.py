from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner
import pytest

from briefly_cli.main import app

runner = CliRunner()


def _make_test_pdf(pages: list[str]) -> bytes:
    """Build a minimal valid PDF with one or more text-bearing pages."""
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
        escaped = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        stream = (
            b"BT /F1 12 Tf 72 720 Td ("
            + escaped.encode("latin-1", errors="replace")
            + b") Tj ET"
        )
        objects.append(
            b"<</Length "
            + str(len(stream)).encode()
            + b">>\nstream\n"
            + stream
            + b"\nendstream"
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

    trailer = (
        b"trailer\n<</Size "
        + str(len(objects) + 1).encode()
        + b"/Root 1 0 R>>\nstartxref\n"
        + str(xref_offset).encode()
        + b"\n%%EOF\n"
    )

    return body + xref + trailer


def _write_sample_pdf(directory: Path, name: str = "sample.pdf", text: str = "Hello PDF") -> Path:
    path = directory / name
    path.write_bytes(_make_test_pdf([text]))
    return path


def test_extract_pdf_prints_text(tmp_path: Path) -> None:
    pdf_path = _write_sample_pdf(tmp_path, text="Document body text")

    result = runner.invoke(app, [str(pdf_path), "--extract"], color=False)

    assert result.exit_code == 0, result.output
    assert "Document body text" in result.output


def test_extract_pdf_json_output(tmp_path: Path) -> None:
    pdf_path = _write_sample_pdf(tmp_path, text="JSON-mode body")

    result = runner.invoke(app, [str(pdf_path), "--extract", "--json"], color=False)

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["input"]["kind"] == "pdf"
    assert payload["input"]["source"] == str(pdf_path)
    assert payload["extracted"]["kind"] == "pdf"
    assert "JSON-mode body" in payload["extracted"]["text"]
    assert payload["summary"] is None


def test_briefing_pdf(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    pdf_path = _write_sample_pdf(tmp_path, text="Briefing input from PDF")

    captured: dict[str, object] = {}

    async def fake_generate_brief(request):
        captured["text"] = request.text
        captured["kind"] = request.input_kind
        captured["model"] = request.options.model
        return type("Result", (), {"text": "BRIEFED", "model": request.options.model})()

    monkeypatch.setattr("briefly_cli.commands.brief.generate_brief", fake_generate_brief)

    result = runner.invoke(
        app,
        [str(pdf_path), "--model", "openai/gpt-5-mini", "--stream", "off"],
        color=False,
    )

    assert result.exit_code == 0, result.output
    assert result.output.strip() == "BRIEFED"
    assert "Briefing input from PDF" in str(captured["text"])
    assert captured["kind"] == "pdf"
    assert captured["model"] == "openai/gpt-5-mini"


def test_pdf_extraction_uses_cache(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    pdf_path = _write_sample_pdf(tmp_path, text="Cached body")

    extract_calls = {"count": 0}
    from briefly_core.pdf import extract_pdf as real_extract_pdf

    def counting_extract(path):
        extract_calls["count"] += 1
        return real_extract_pdf(path)

    monkeypatch.setattr("briefly_cli.commands.brief.extract_pdf", counting_extract)

    first = runner.invoke(app, [str(pdf_path), "--extract"], color=False)
    assert first.exit_code == 0, first.output
    second = runner.invoke(app, [str(pdf_path), "--extract"], color=False)
    assert second.exit_code == 0, second.output

    assert extract_calls["count"] == 1
    assert first.output == second.output


def test_pdf_cache_invalidated_on_mtime_change(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    pdf_path = _write_sample_pdf(tmp_path, text="Original body")

    extract_calls = {"count": 0}
    from briefly_core.pdf import extract_pdf as real_extract_pdf

    def counting_extract(path):
        extract_calls["count"] += 1
        return real_extract_pdf(path)

    monkeypatch.setattr("briefly_cli.commands.brief.extract_pdf", counting_extract)

    first = runner.invoke(app, [str(pdf_path), "--extract"], color=False)
    assert first.exit_code == 0, first.output

    pdf_path.write_bytes(_make_test_pdf(["Updated body"]))
    new_time = pdf_path.stat().st_mtime + 5
    import os

    os.utime(pdf_path, (new_time, new_time))

    second = runner.invoke(app, [str(pdf_path), "--extract"], color=False)
    assert second.exit_code == 0, second.output

    assert extract_calls["count"] == 2
    assert "Updated body" in second.output


def test_pdf_skip_cache_re_extracts(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    pdf_path = _write_sample_pdf(tmp_path, text="Repeat extraction body")

    extract_calls = {"count": 0}
    from briefly_core.pdf import extract_pdf as real_extract_pdf

    def counting_extract(path):
        extract_calls["count"] += 1
        return real_extract_pdf(path)

    monkeypatch.setattr("briefly_cli.commands.brief.extract_pdf", counting_extract)

    first = runner.invoke(app, [str(pdf_path), "--extract", "--skip-cache"], color=False)
    assert first.exit_code == 0, first.output
    second = runner.invoke(app, [str(pdf_path), "--extract", "--skip-cache"], color=False)
    assert second.exit_code == 0, second.output

    assert extract_calls["count"] == 2
