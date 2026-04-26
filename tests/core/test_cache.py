from pathlib import Path
import sqlite3
import time

from briefly_core.briefing import BriefingOptions, build_briefing_request
from briefly_core.cache import (
    clear_cache,
    get_cache_stats,
    get_summary_cache,
    get_url_cache,
    resolve_cache_path,
    set_summary_cache,
    set_url_cache,
    summary_cache_key,
)
from briefly_core.content import ExtractedContent
from briefly_core.flags import LengthArg
from briefly_core.input import ResolvedInput


def _request(
    *,
    model: str = "test/model",
    length: LengthArg | None = None,
    output_format: str = "text",
):
    return build_briefing_request(
        ResolvedInput(kind="text", source="literal", text="Cache this."),
        BriefingOptions(
            length=length or LengthArg(kind="preset", preset="medium"),
            output_format=output_format,
            model=model,
        ),
    )


def test_resolves_cache_path(tmp_path: Path) -> None:
    assert resolve_cache_path({"HOME": str(tmp_path)}) == tmp_path / ".briefly" / "cache.sqlite"
    assert resolve_cache_path(
        {"BRIEFLY_CONFIG": str(tmp_path / "custom" / "config.json"), "HOME": "ignored"}
    ) == tmp_path / "custom" / "cache.sqlite"
    assert resolve_cache_path({}) is None


def test_url_cache_round_trip(tmp_path: Path) -> None:
    cache_path = tmp_path / "cache.sqlite"
    extracted = ExtractedContent(
        source="https://example.com/final",
        title="Example",
        text="Cached page text.",
    )

    assert get_url_cache("https://example.com", cache_path=cache_path) is None

    set_url_cache("https://example.com", extracted, cache_path=cache_path)

    assert get_url_cache("https://example.com", cache_path=cache_path) == extracted


def test_summary_cache_round_trip(tmp_path: Path) -> None:
    cache_path = tmp_path / "cache.sqlite"
    request = _request()

    assert get_summary_cache(request, cache_path=cache_path) is None

    set_summary_cache(request, "Cached brief.", cache_path=cache_path)

    cached = get_summary_cache(request, cache_path=cache_path)
    assert cached is not None
    assert cached.text == "Cached brief."


def test_summary_cache_key_changes_with_options() -> None:
    base = _request()
    long = _request(length=LengthArg(kind="preset", preset="long"))
    markdown = _request(output_format="markdown")
    other_model = _request(model="other/model")

    assert summary_cache_key(base) != summary_cache_key(long)
    assert summary_cache_key(base) != summary_cache_key(markdown)
    assert summary_cache_key(base) != summary_cache_key(other_model)


def test_url_cache_expires_after_ttl(tmp_path: Path) -> None:
    cache_path = tmp_path / "cache.sqlite"
    extracted = ExtractedContent(
        source="https://example.com/final",
        title="Example",
        text="Cached page text.",
    )
    set_url_cache("https://example.com", extracted, cache_path=cache_path)

    _age_cache_row(cache_path, "url_cache", days=8)

    assert get_url_cache("https://example.com", cache_path=cache_path) is None
    assert get_url_cache("https://example.com", cache_path=cache_path, ttl_days=9) == extracted


def test_summary_cache_expires_after_ttl(tmp_path: Path) -> None:
    cache_path = tmp_path / "cache.sqlite"
    request = _request()
    set_summary_cache(request, "Cached brief.", cache_path=cache_path)

    _age_cache_row(cache_path, "summary_cache", days=31)

    assert get_summary_cache(request, cache_path=cache_path) is None
    cached = get_summary_cache(request, cache_path=cache_path, ttl_days=32)
    assert cached is not None
    assert cached.text == "Cached brief."


def test_cache_stats_and_clear(tmp_path: Path) -> None:
    cache_path = tmp_path / "cache.sqlite"
    extracted = ExtractedContent(
        source="https://example.com/final",
        title="Example",
        text="Cached page text.",
    )
    request = _request()
    set_url_cache("https://example.com", extracted, cache_path=cache_path)
    set_summary_cache(request, "Cached brief.", cache_path=cache_path)

    stats = get_cache_stats(cache_path=cache_path)
    assert stats.exists is True
    assert stats.url_entries == 1
    assert stats.summary_entries == 1
    assert stats.size_bytes > 0

    cleared = clear_cache(cache_path=cache_path)
    assert cleared.url_entries == 1
    assert cleared.summary_entries == 1

    stats = get_cache_stats(cache_path=cache_path)
    assert stats.url_entries == 0
    assert stats.summary_entries == 0


def _age_cache_row(cache_path: Path, table: str, *, days: float) -> None:
    stale_time = time.time() - (days * 24 * 60 * 60)
    with sqlite3.connect(cache_path) as connection:
        connection.execute(f"UPDATE {table} SET created_at = ?", (stale_time,))
