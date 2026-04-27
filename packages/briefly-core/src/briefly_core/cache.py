from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import time
from typing import Any, Mapping

from briefly_core.briefing import BriefingRequest
from briefly_core.content import ExtractedContent

_URL_EXTRACT_VERSION = 1
_SUMMARY_PROMPT_VERSION = 1
_DEFAULT_URL_TTL_DAYS = 7.0
_DEFAULT_SUMMARY_TTL_DAYS = 30.0


@dataclass(frozen=True)
class SummaryCacheEntry:
    text: str


@dataclass(frozen=True)
class CacheStats:
    path: Path | None
    exists: bool
    url_entries: int
    summary_entries: int
    size_bytes: int


@dataclass(frozen=True)
class ClearedCache:
    path: Path | None
    url_entries: int
    summary_entries: int


def resolve_cache_path(env: Mapping[str, str | None] | None = None) -> Path | None:
    values = os.environ if env is None else env

    explicit_config_path = _clean_string(values.get("BRIEFLY_CONFIG"))
    if explicit_config_path:
        return Path(explicit_config_path).expanduser().parent / "cache.sqlite"

    home = _clean_string(values.get("HOME")) or _clean_string(values.get("USERPROFILE"))
    if not home:
        return None

    return Path(home).expanduser() / ".briefly" / "cache.sqlite"


def get_url_cache(
    requested_url: str,
    *,
    output_format: str = "text",
    cache_path: Path | None = None,
    ttl_days: float | None = _DEFAULT_URL_TTL_DAYS,
) -> ExtractedContent | None:
    path = cache_path or resolve_cache_path()
    if path is None or not path.exists():
        return None

    key = url_cache_key(requested_url, output_format=output_format)
    with _connect(path) as connection:
        row = connection.execute(
            "SELECT source, title, text, created_at FROM url_cache WHERE key = ?",
            (key,),
        ).fetchone()

    if row is None:
        return None
    if _is_expired(row[3], ttl_days):
        return None
    return ExtractedContent(source=row[0], title=row[1], text=row[2])


def set_url_cache(
    requested_url: str,
    extracted: ExtractedContent,
    *,
    output_format: str = "text",
    cache_path: Path | None = None,
) -> None:
    path = cache_path or resolve_cache_path()
    if path is None:
        return

    key = url_cache_key(requested_url, output_format=output_format)
    path.parent.mkdir(parents=True, exist_ok=True)
    with _connect(path) as connection:
        _ensure_schema(connection)
        connection.execute(
            """
            INSERT OR REPLACE INTO url_cache
                (key, requested_url, source, title, text, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (key, requested_url, extracted.source, extracted.title, extracted.text, time.time()),
        )


def get_summary_cache(
    request: BriefingRequest,
    *,
    cache_path: Path | None = None,
    ttl_days: float | None = _DEFAULT_SUMMARY_TTL_DAYS,
) -> SummaryCacheEntry | None:
    path = cache_path or resolve_cache_path()
    if path is None or not path.exists():
        return None

    key = summary_cache_key(request)
    with _connect(path) as connection:
        row = connection.execute(
            "SELECT text, created_at FROM summary_cache WHERE key = ?",
            (key,),
        ).fetchone()

    if row is None:
        return None
    if _is_expired(row[1], ttl_days):
        return None
    return SummaryCacheEntry(text=row[0])


def set_summary_cache(
    request: BriefingRequest,
    text: str,
    *,
    cache_path: Path | None = None,
) -> None:
    path = cache_path or resolve_cache_path()
    if path is None:
        return

    key = summary_cache_key(request)
    path.parent.mkdir(parents=True, exist_ok=True)
    with _connect(path) as connection:
        _ensure_schema(connection)
        connection.execute(
            """
            INSERT OR REPLACE INTO summary_cache
                (key, input_kind, source, model, text, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                key,
                request.input_kind,
                request.source,
                request.options.model,
                text,
                time.time(),
            ),
        )


def get_cache_stats(*, cache_path: Path | None = None) -> CacheStats:
    path = cache_path or resolve_cache_path()
    if path is None:
        return CacheStats(path=None, exists=False, url_entries=0, summary_entries=0, size_bytes=0)

    if not path.exists():
        return CacheStats(path=path, exists=False, url_entries=0, summary_entries=0, size_bytes=0)

    with _connect(path) as connection:
        url_entries = _count_rows(connection, "url_cache")
        summary_entries = _count_rows(connection, "summary_cache")

    return CacheStats(
        path=path,
        exists=True,
        url_entries=url_entries,
        summary_entries=summary_entries,
        size_bytes=path.stat().st_size,
    )


def clear_cache(*, cache_path: Path | None = None) -> ClearedCache:
    path = cache_path or resolve_cache_path()
    if path is None or not path.exists():
        return ClearedCache(path=path, url_entries=0, summary_entries=0)

    with _connect(path) as connection:
        url_entries = _count_rows(connection, "url_cache")
        summary_entries = _count_rows(connection, "summary_cache")
        connection.execute("DELETE FROM url_cache")
        connection.execute("DELETE FROM summary_cache")

    return ClearedCache(path=path, url_entries=url_entries, summary_entries=summary_entries)


def url_cache_key(requested_url: str, *, output_format: str = "text") -> str:
    return _hash_payload(
        {
            "type": "url_extract",
            "version": _URL_EXTRACT_VERSION,
            "url": requested_url,
            "output_format": output_format,
        }
    )


def summary_cache_key(request: BriefingRequest) -> str:
    return _hash_payload(
        {
            "type": "summary",
            "version": _SUMMARY_PROMPT_VERSION,
            "input_kind": request.input_kind,
            "source": request.source,
            "text_hash": _hash_text(request.text),
            "model": request.options.model,
            "length": {
                "kind": request.options.length.kind,
                "preset": request.options.length.preset,
                "max_characters": request.options.length.max_characters,
            },
            "output_format": request.options.output_format,
            "max_input_chars": request.options.max_input_chars,
            "max_output_tokens": request.options.max_output_tokens,
        }
    )


def _connect(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(path)
    _ensure_schema(connection)
    return connection


def _ensure_schema(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS url_cache (
            key TEXT PRIMARY KEY,
            requested_url TEXT NOT NULL,
            source TEXT NOT NULL,
            title TEXT,
            text TEXT NOT NULL,
            created_at REAL NOT NULL
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS summary_cache (
            key TEXT PRIMARY KEY,
            input_kind TEXT NOT NULL,
            source TEXT NOT NULL,
            model TEXT,
            text TEXT NOT NULL,
            created_at REAL NOT NULL
        )
        """
    )


def _count_rows(connection: sqlite3.Connection, table: str) -> int:
    row = connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
    return int(row[0])


def _is_expired(created_at: float, ttl_days: float | None) -> bool:
    if ttl_days is None:
        return False
    return created_at < time.time() - (ttl_days * 24 * 60 * 60)


def _hash_payload(payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _clean_string(raw: str | None) -> str | None:
    if raw is None:
        return None
    value = raw.strip()
    return value or None
