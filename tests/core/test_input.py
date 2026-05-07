from pathlib import Path

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
