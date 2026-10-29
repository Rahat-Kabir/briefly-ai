import codecs
from pathlib import Path

import pytest

from briefly_core.input import ResolvedInput, resolve_input_target


def test_resolves_literal_text() -> None:
    assert resolve_input_target("Briefly reads text.") == ResolvedInput(
        kind="text",
        source="literal",
        text="Briefly reads text.",
    )


def test_resolves_local_file(tmp_path: Path) -> None:
    source = tmp_path / "notes.txt"
    source.write_text("Briefly reads files.", encoding="utf-8")

    assert resolve_input_target(str(source)) == ResolvedInput(
        kind="file",
        source=str(source),
        text="Briefly reads files.",
    )


def test_resolves_stdin() -> None:
    assert resolve_input_target("-", stdin_reader=lambda: "Briefly reads stdin.") == ResolvedInput(
        kind="stdin",
        source="-",
        text="Briefly reads stdin.",
    )


def test_resolves_http_url_without_extracting() -> None:
    assert resolve_input_target("https://example.com") == ResolvedInput(
        kind="url",
        source="https://example.com",
        text=None,
    )


def test_resolves_pdf_file_without_reading(tmp_path: Path) -> None:
    pdf_path = tmp_path / "paper.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n")

    assert resolve_input_target(str(pdf_path)) == ResolvedInput(
        kind="pdf",
        source=str(pdf_path),
        text=None,
    )


def test_resolves_audio_file_without_reading(tmp_path: Path) -> None:
    audio_path = tmp_path / "meeting.mp3"
    audio_path.write_bytes(b"audio")

    assert resolve_input_target(str(audio_path)) == ResolvedInput(
        kind="audio",
        source=str(audio_path),
        text=None,
    )


def test_resolves_video_file_without_reading(tmp_path: Path) -> None:
    video_path = tmp_path / "lecture.mp4"
    video_path.write_bytes(b"video")

    assert resolve_input_target(str(video_path)) == ResolvedInput(
        kind="video",
        source=str(video_path),
        text=None,
    )


@pytest.mark.parametrize(
    "raw",
    [
        "Briefly reads files.\r\nLine two.".encode("utf-16"),
        codecs.BOM_UTF16_BE + "Briefly reads files.\r\nLine two.".encode("utf-16-be"),
        codecs.BOM_UTF8 + "Briefly reads files.\r\nLine two.".encode("utf-8"),
    ],
    ids=["utf-16-le-bom", "utf-16-be-bom", "utf-8-bom"],
)
def test_file_with_bom_is_decoded(tmp_path: Path, raw: bytes) -> None:
    source = tmp_path / "notes.txt"
    source.write_bytes(raw)

    resolved = resolve_input_target(str(source))

    assert resolved.text == "Briefly reads files.\nLine two."


@pytest.mark.parametrize(
    "raw",
    [
        "nope.txt",
        "notes/meeting.md",
        r"C:\Users\me\my notes.txt",
        "/home/me/my notes.txt",
        "~/my notes.txt",
        "report.pdf",
        "example.com",
    ],
)
def test_missing_file_path_raises_clear_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, raw: str
) -> None:
    monkeypatch.chdir(tmp_path)

    with pytest.raises(ValueError, match="File not found"):
        resolve_input_target(raw)


def test_folder_path_raises_clear_error(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="Input is a folder, not a file"):
        resolve_input_target(str(tmp_path))


@pytest.mark.parametrize(
    "raw",
    [
        "Read the docs at notes.md",
        "I love Python.",
        "v1.2",
        "First line\nsee notes.md",
        "Summarize the pros/cons of Node.js",
        "Compare TCP/IP and example.com",
    ],
)
def test_text_that_mentions_a_file_stays_text(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, raw: str
) -> None:
    monkeypatch.chdir(tmp_path)

    assert resolve_input_target(raw).kind == "text"


def test_non_utf8_file_raises_clear_error(tmp_path: Path) -> None:
    source = tmp_path / "notes.txt"
    source.write_bytes("café".encode("latin-1"))

    with pytest.raises(ValueError, match="File is not UTF-8 or UTF-16 text"):
        resolve_input_target(str(source))
