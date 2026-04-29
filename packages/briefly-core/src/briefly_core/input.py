from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Literal
from urllib.parse import urlparse

InputKind = Literal["text", "file", "stdin", "url", "pdf"]


@dataclass(frozen=True)
class ResolvedInput:
    kind: InputKind
    source: str
    text: str | None


def resolve_input_target(
    raw_input: str,
    *,
    stdin_reader: Callable[[], str] | None = None,
) -> ResolvedInput:
    if raw_input == "-":
        if stdin_reader is None:
            raise ValueError("stdin input requires a reader")
        return ResolvedInput(kind="stdin", source="-", text=stdin_reader())

    if _is_http_url(raw_input):
        return ResolvedInput(kind="url", source=raw_input, text=None)

    path = Path(raw_input).expanduser()
    if path.exists() and path.is_file():
        if path.suffix.lower() == ".pdf":
            return ResolvedInput(kind="pdf", source=str(path), text=None)
        return ResolvedInput(kind="file", source=str(path), text=path.read_text(encoding="utf-8"))

    return ResolvedInput(kind="text", source="literal", text=raw_input)


def _is_http_url(raw_input: str) -> bool:
    parsed = urlparse(raw_input)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)
