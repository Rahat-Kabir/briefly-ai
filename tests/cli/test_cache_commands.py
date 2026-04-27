import json
from pathlib import Path
import sqlite3
import time

from click.testing import CliRunner

from briefly_cli.main import app
from briefly_core.briefing import BriefingOptions, build_briefing_request
from briefly_core.cache import set_summary_cache, set_url_cache
from briefly_core.content import ExtractedContent
from briefly_core.flags import LengthArg
from briefly_core.input import ResolvedInput

runner = CliRunner()


def test_cache_stats_reports_counts(tmp_path: Path) -> None:
    cache_path = tmp_path / ".briefly" / "cache.sqlite"
    _seed_cache(cache_path)

    result = runner.invoke(app, ["cache", "stats"], color=False)

    assert result.exit_code == 0
    assert f"Cache: {cache_path}" in result.output
    assert "Exists: yes" in result.output
    assert "URL entries: 1" in result.output
    assert "Summary entries: 1" in result.output


def test_cache_clear_removes_entries(tmp_path: Path) -> None:
    cache_path = tmp_path / ".briefly" / "cache.sqlite"
    _seed_cache(cache_path)

    result = runner.invoke(app, ["cache", "clear"], color=False)

    assert result.exit_code == 0
    assert f"Cleared cache: {cache_path}" in result.output
    assert "URL entries removed: 1" in result.output
    assert "Summary entries removed: 1" in result.output

    stats = runner.invoke(app, ["cache", "stats"], color=False)
    assert "URL entries: 0" in stats.output
    assert "Summary entries: 0" in stats.output


def test_configured_ttl_expires_summary_cache(monkeypatch, tmp_path: Path) -> None:
    _write_config(tmp_path, {"model": "test/model", "cache": {"ttlDays": 1}})
    calls = 0

    async def fake_generate_brief(request):
        nonlocal calls
        calls += 1
        return type("Result", (), {"text": f"Brief {calls}."})()

    monkeypatch.setattr("briefly_cli.commands.brief.generate_brief", fake_generate_brief)

    first = runner.invoke(app, ["Source text.", "--stream", "off"], color=False)
    _age_cache_table(tmp_path / ".briefly" / "cache.sqlite", "summary_cache", days=2)
    second = runner.invoke(app, ["Source text.", "--stream", "off"], color=False)

    assert first.exit_code == 0
    assert second.exit_code == 0
    assert first.output == "Brief 1.\n"
    assert second.output == "Brief 2.\n"
    assert calls == 2


def test_configured_ttl_expires_url_cache(monkeypatch, tmp_path: Path) -> None:
    _write_config(tmp_path, {"cache": {"ttlDays": 1}})
    calls = 0

    async def fake_extract_url(url: str, **kwargs):
        nonlocal calls
        calls += 1
        return type(
            "Extracted",
            (),
            {
                "source": f"https://example.com/{calls}",
                "title": f"Title {calls}",
                "text": f"Text {calls}.",
            },
        )()

    monkeypatch.setattr("briefly_cli.commands.brief.extract_url", fake_extract_url)

    first = runner.invoke(app, ["https://example.com", "--extract"], color=False)
    _age_cache_table(tmp_path / ".briefly" / "cache.sqlite", "url_cache", days=2)
    second = runner.invoke(app, ["https://example.com", "--extract"], color=False)

    assert first.exit_code == 0
    assert second.exit_code == 0
    assert first.output == "Title 1\n\nText 1.\n"
    assert second.output == "Title 2\n\nText 2.\n"
    assert calls == 2


def _write_config(tmp_path: Path, value: object) -> None:
    config_path = tmp_path / ".briefly" / "config.json"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(json.dumps(value), encoding="utf-8")


def _seed_cache(cache_path: Path) -> None:
    extracted = ExtractedContent(
        source="https://example.com/final",
        title="Example",
        text="Cached page text.",
    )
    request = build_briefing_request(
        ResolvedInput(kind="text", source="literal", text="Cache this."),
        BriefingOptions(
            length=LengthArg(kind="preset", preset="medium"),
            output_format="text",
            model="test/model",
        ),
    )
    set_url_cache("https://example.com", extracted, cache_path=cache_path)
    set_summary_cache(request, "Cached brief.", cache_path=cache_path)


def _age_cache_table(cache_path: Path, table: str, *, days: float) -> None:
    if table not in {"summary_cache", "url_cache"}:
        raise ValueError(f"Unsupported cache table: {table}")
    stale_time = time.time() - (days * 24 * 60 * 60)
    with sqlite3.connect(cache_path) as connection:
        connection.execute(f"UPDATE {table} SET created_at = ?", (stale_time,))
