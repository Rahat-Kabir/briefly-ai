"""Briefly CLI flag parsers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal
import re

YoutubeMode = Literal["auto", "web", "apify", "yt-dlp", "no-auto"]
FirecrawlMode = Literal["off", "auto", "always"]
MarkdownMode = Literal["off", "auto", "llm", "readability"]
ExtractFormat = Literal["text", "markdown"]
PreprocessMode = Literal["off", "auto", "always"]
StreamMode = Literal["auto", "on", "off"]
MetricsMode = Literal["off", "on", "detailed"]
VideoMode = Literal["auto", "transcript", "understand"]
BriefLength = Literal["short", "medium", "long", "xl", "xxl"]
BriefType = Literal["standard", "executive", "action", "study", "decision"]

BRIEF_LENGTHS: tuple[BriefLength, ...] = ("short", "medium", "long", "xl", "xxl")
BRIEF_TYPES: tuple[BriefType, ...] = (
    "standard",
    "executive",
    "action",
    "study",
    "decision",
)
_DURATION_PATTERN = re.compile(r"^(?P<value>\d+(?:\.\d+)?)(?P<unit>ms|s|m|h)?$", re.I)
_COUNT_PATTERN = re.compile(r"^(?P<value>\d+(?:\.\d+)?)(?P<unit>k|m)?$", re.I)
_MIN_LENGTH_CHARS = 10
_MIN_MAX_OUTPUT_TOKENS = 16
_MIN_RETRIES = 0
_MAX_RETRIES = 5


@dataclass(frozen=True)
class LengthArg:
    kind: Literal["preset", "chars"]
    preset: BriefLength | None = None
    max_characters: int | None = None


def parse_youtube_mode(raw: str) -> YoutubeMode:
    normalized = raw.strip().lower()
    if normalized == "autp":
        return "auto"
    if normalized in {"auto", "web", "apify", "yt-dlp", "no-auto"}:
        return normalized  # type: ignore[return-value]
    raise ValueError(f"Unsupported --youtube: {raw}")


def parse_firecrawl_mode(raw: str) -> FirecrawlMode:
    normalized = raw.strip().lower()
    if normalized in {"off", "auto", "always"}:
        return normalized  # type: ignore[return-value]
    raise ValueError(f"Unsupported --firecrawl: {raw}")


def parse_markdown_mode(raw: str) -> MarkdownMode:
    normalized = raw.strip().lower()
    if normalized in {"off", "auto", "llm", "readability"}:
        return normalized  # type: ignore[return-value]
    raise ValueError(f"Unsupported --markdown-mode: {raw}")


def parse_extract_format(raw: str) -> ExtractFormat:
    normalized = raw.strip().lower()
    if normalized in {"text", "txt", "plain"}:
        return "text"
    if normalized in {"md", "markdown"}:
        return "markdown"
    raise ValueError(f"Unsupported --format: {raw}")


def parse_preprocess_mode(raw: str) -> PreprocessMode:
    normalized = raw.strip().lower()
    if normalized in {"off", "auto", "always"}:
        return normalized  # type: ignore[return-value]
    if normalized == "on":
        return "always"
    raise ValueError(f"Unsupported --preprocess: {raw}")


def parse_stream_mode(raw: str) -> StreamMode:
    normalized = raw.strip().lower()
    if normalized in {"auto", "on", "off"}:
        return normalized  # type: ignore[return-value]
    raise ValueError(f"Unsupported --stream: {raw}")


def parse_metrics_mode(raw: str) -> MetricsMode:
    normalized = raw.strip().lower()
    if normalized in {"off", "on", "detailed"}:
        return normalized  # type: ignore[return-value]
    raise ValueError(f"Unsupported --metrics: {raw}")


def parse_video_mode(raw: str) -> VideoMode:
    normalized = raw.strip().lower()
    if normalized in {"auto", "transcript", "understand"}:
        return normalized  # type: ignore[return-value]
    raise ValueError(f"Unsupported --video-mode: {raw}")


def parse_brief_type(raw: str) -> BriefType:
    normalized = raw.strip().lower()
    if normalized in BRIEF_TYPES:
        return normalized  # type: ignore[return-value]
    raise ValueError(f"Unsupported --brief-type: {raw}")


def parse_duration_ms(raw: str) -> int:
    normalized = raw.strip()
    match = _DURATION_PATTERN.fullmatch(normalized)
    if not match:
        raise ValueError(f"Unsupported --timeout: {raw}")

    numeric = float(match.group("value"))
    if numeric <= 0:
        raise ValueError(f"Unsupported --timeout: {raw}")

    unit = (match.group("unit") or "s").lower()
    multiplier = {"ms": 1, "s": 1000, "m": 60_000, "h": 3_600_000}[unit]
    return int(numeric * multiplier)


def parse_length_arg(raw: str) -> LengthArg:
    normalized = raw.strip().lower()
    shorthand: dict[str, BriefLength] = {"s": "short", "m": "medium", "l": "long"}
    if normalized in shorthand:
        return LengthArg(kind="preset", preset=shorthand[normalized])

    if normalized in BRIEF_LENGTHS:
        return LengthArg(kind="preset", preset=normalized)  # type: ignore[arg-type]

    match = _COUNT_PATTERN.fullmatch(normalized)
    if not match:
        raise ValueError(f"Unsupported --length: {raw}")

    numeric = float(match.group("value"))
    if numeric <= 0:
        raise ValueError(f"Unsupported --length: {raw}")

    multiplier = _count_multiplier(match.group("unit"))
    max_characters = int(numeric * multiplier)
    if max_characters < _MIN_LENGTH_CHARS:
        raise ValueError(f"Unsupported --length: {raw} (minimum {_MIN_LENGTH_CHARS} chars)")
    return LengthArg(kind="chars", max_characters=max_characters)


def parse_max_extract_characters(raw: str | None) -> int | None:
    if raw is None:
        return None
    normalized = raw.strip().lower()
    if not normalized:
        return None

    match = _COUNT_PATTERN.fullmatch(normalized)
    if not match:
        raise ValueError(f"Unsupported --max-extract-characters: {raw}")

    numeric = float(match.group("value"))
    if numeric <= 0:
        return None

    max_characters = int(numeric * _count_multiplier(match.group("unit")))
    if max_characters < _MIN_LENGTH_CHARS:
        raise ValueError(
            f"Unsupported --max-extract-characters: {raw} "
            f"(minimum {_MIN_LENGTH_CHARS} chars)"
        )
    return max_characters


def parse_max_output_tokens(raw: str | None) -> int | None:
    if raw is None:
        return None
    normalized = raw.strip().lower()
    if not normalized:
        raise ValueError(f"Unsupported --max-output-tokens: {raw}")

    match = _COUNT_PATTERN.fullmatch(normalized)
    if not match:
        raise ValueError(f"Unsupported --max-output-tokens: {raw}")

    numeric = float(match.group("value"))
    if numeric <= 0:
        raise ValueError(f"Unsupported --max-output-tokens: {raw}")

    max_output_tokens = int(numeric * _count_multiplier(match.group("unit")))
    if max_output_tokens < _MIN_MAX_OUTPUT_TOKENS:
        raise ValueError(
            f"Unsupported --max-output-tokens: {raw} (minimum {_MIN_MAX_OUTPUT_TOKENS})"
        )
    return max_output_tokens


def parse_retries(raw: str) -> int:
    normalized = raw.strip()
    if not normalized:
        raise ValueError(f"Unsupported --retries: {raw}")

    try:
        numeric = float(normalized)
    except ValueError as error:
        raise ValueError(f"Unsupported --retries: {raw}") from error

    if not numeric.is_integer():
        raise ValueError(f"Unsupported --retries: {raw}")

    retries = int(numeric)
    if retries < _MIN_RETRIES or retries > _MAX_RETRIES:
        raise ValueError(f"Unsupported --retries: {raw} (range {_MIN_RETRIES}-{_MAX_RETRIES})")
    return retries


def _count_multiplier(unit: str | None) -> int:
    normalized = (unit or "").lower()
    if normalized == "k":
        return 1000
    if normalized == "m":
        return 1_000_000
    return 1
