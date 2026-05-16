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


_DEFAULT_SAMPLE_TEXT = (
    "This is a substantive paragraph of document body text used for "
    "testing the PDF extraction pipeline end to end."
)


def _write_sample_pdf(
    directory: Path,
    name: str = "sample.pdf",
    text: str = _DEFAULT_SAMPLE_TEXT,
) -> Path:
    path = directory / name
    path.write_bytes(_make_test_pdf([text]))
    return path


def test_extract_pdf_prints_text(tmp_path: Path) -> None:
    pdf_path = _write_sample_pdf(
        tmp_path,
        text="Document body text padded with extra words for the extractable threshold.",
    )

    result = runner.invoke(app, [str(pdf_path), "--extract"], color=False)

    assert result.exit_code == 0, result.stdout
    assert "Document body text" in result.stdout


def test_extract_pdf_json_output(tmp_path: Path) -> None:
    pdf_path = _write_sample_pdf(
        tmp_path,
        text="JSON-mode body padded with extra words to clear the extractable threshold.",
    )

    result = runner.invoke(app, [str(pdf_path), "--extract", "--json"], color=False)

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["input"]["kind"] == "pdf"
    assert payload["input"]["source"] == str(pdf_path)
    assert payload["extracted"]["kind"] == "pdf"
    assert "JSON-mode body" in payload["extracted"]["text"]
    assert payload["summary"] is None


def test_briefing_pdf(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    pdf_path = _write_sample_pdf(
        tmp_path,
        text="Briefing input from PDF padded with extra words to clear the threshold.",
    )

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

    assert result.exit_code == 0, result.stdout
    assert result.stdout.strip() == "BRIEFED"
    assert "Briefing input from PDF" in str(captured["text"])
    assert captured["kind"] == "pdf"
    assert captured["model"] == "openai/gpt-5-mini"


def test_pdf_extraction_uses_cache(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    pdf_path = _write_sample_pdf(
        tmp_path,
        text="Cached body padded with extra words to clear the extractable threshold.",
    )

    extract_calls = {"count": 0}
    from briefly_core.pdf import extract_pdf as real_extract_pdf

    def counting_extract(path):
        extract_calls["count"] += 1
        return real_extract_pdf(path)

    monkeypatch.setattr("briefly_cli.commands.brief.extract_pdf", counting_extract)

    first = runner.invoke(app, [str(pdf_path), "--extract"], color=False)
    assert first.exit_code == 0, first.stdout
    second = runner.invoke(app, [str(pdf_path), "--extract"], color=False)
    assert second.exit_code == 0, second.stdout

    assert extract_calls["count"] == 1
    assert first.stdout == second.stdout


def test_pdf_cache_invalidated_on_mtime_change(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    pdf_path = _write_sample_pdf(
        tmp_path,
        text="Original body padded with extra words to clear the extractable threshold.",
    )

    extract_calls = {"count": 0}
    from briefly_core.pdf import extract_pdf as real_extract_pdf

    def counting_extract(path):
        extract_calls["count"] += 1
        return real_extract_pdf(path)

    monkeypatch.setattr("briefly_cli.commands.brief.extract_pdf", counting_extract)

    first = runner.invoke(app, [str(pdf_path), "--extract"], color=False)
    assert first.exit_code == 0, first.stdout

    pdf_path.write_bytes(
        _make_test_pdf(
            ["Updated body padded with extra words to clear the extractable threshold."]
        )
    )
    new_time = pdf_path.stat().st_mtime + 5
    import os

    os.utime(pdf_path, (new_time, new_time))

    second = runner.invoke(app, [str(pdf_path), "--extract"], color=False)
    assert second.exit_code == 0, second.stdout

    assert extract_calls["count"] == 2
    assert "Updated body" in second.stdout


def test_pdf_skip_cache_re_extracts(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    pdf_path = _write_sample_pdf(
        tmp_path,
        text="Repeat extraction body padded with extra words to clear the threshold.",
    )

    extract_calls = {"count": 0}
    from briefly_core.pdf import extract_pdf as real_extract_pdf

    def counting_extract(path):
        extract_calls["count"] += 1
        return real_extract_pdf(path)

    monkeypatch.setattr("briefly_cli.commands.brief.extract_pdf", counting_extract)

    first = runner.invoke(app, [str(pdf_path), "--extract", "--skip-cache"], color=False)
    assert first.exit_code == 0, first.stdout
    second = runner.invoke(app, [str(pdf_path), "--extract", "--skip-cache"], color=False)
    assert second.exit_code == 0, second.stdout

    assert extract_calls["count"] == 2


def test_scanned_pdf_uses_vision_fallback(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    pdf_path = _write_sample_pdf(tmp_path, name="scanned.pdf", text="")

    fallback_calls: list[str] = []

    async def fake_vision(path: Path, model: str):
        fallback_calls.append(model)
        from briefly_core.content import ExtractedContent

        return ExtractedContent(source=str(path), title=path.stem, text="OCR text from PDF.")

    monkeypatch.setattr(
        "briefly_cli.commands.brief.extract_pdf_via_vision", fake_vision
    )

    result = runner.invoke(
        app,
        [
            str(pdf_path),
            "--extract",
            "--vision-model",
            "gemini/gemini-2.5-flash-lite",
        ],
        color=False,
    )

    assert result.exit_code == 0, result.stdout
    assert "OCR text from PDF." in result.stdout
    assert fallback_calls == ["gemini/gemini-2.5-flash-lite"]


def test_scanned_pdf_without_vision_model_errors(tmp_path: Path) -> None:
    pdf_path = _write_sample_pdf(tmp_path, name="scanned.pdf", text="")

    result = runner.invoke(app, [str(pdf_path), "--extract"], color=False)

    assert result.exit_code != 0
    assert "scanned" in result.stderr.lower() or "vision.model" in result.stderr


def test_text_pdf_does_not_call_vision_fallback(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    pdf_path = _write_sample_pdf(tmp_path)

    async def fail_vision(*_args, **_kwargs):  # pragma: no cover - must not be called
        raise AssertionError("Vision fallback should not run for text-layer PDFs.")

    monkeypatch.setattr(
        "briefly_cli.commands.brief.extract_pdf_via_vision", fail_vision
    )

    result = runner.invoke(
        app,
        [
            str(pdf_path),
            "--extract",
            "--vision-model",
            "gemini/gemini-2.5-flash-lite",
        ],
        color=False,
    )

    assert result.exit_code == 0, result.stdout


def test_scanned_pdf_cache_invalidates_on_vision_model_change(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    pdf_path = _write_sample_pdf(tmp_path, name="scanned.pdf", text="")
    calls: list[str] = []

    async def fake_vision(path: Path, model: str):
        calls.append(model)
        from briefly_core.content import ExtractedContent

        return ExtractedContent(
            source=str(path),
            title=path.stem,
            text=f"OCR via {model}.",
        )

    monkeypatch.setattr(
        "briefly_cli.commands.brief.extract_pdf_via_vision", fake_vision
    )

    runner.invoke(
        app,
        [str(pdf_path), "--extract", "--vision-model", "gemini/gemini-2.5-flash-lite"],
        color=False,
    )
    runner.invoke(
        app,
        [str(pdf_path), "--extract", "--vision-model", "gemini/gemini-2.5-flash-lite"],
        color=False,
    )
    runner.invoke(
        app,
        [str(pdf_path), "--extract", "--vision-model", "gemini/gemini-2.5-flash"],
        color=False,
    )

    assert calls == [
        "gemini/gemini-2.5-flash-lite",
        "gemini/gemini-2.5-flash",
    ]
