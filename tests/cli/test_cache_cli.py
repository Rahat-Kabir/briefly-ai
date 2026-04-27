from click.testing import CliRunner

from briefly_cli.main import app

runner = CliRunner()


def test_url_cache_hit_avoids_extract_url(monkeypatch) -> None:
    calls = 0

    async def fake_extract_url(url: str):
        nonlocal calls
        calls += 1
        return type(
            "Extracted",
            (),
            {
                "source": "https://example.com/final",
                "title": "Example",
                "text": "Cached page text.",
            },
        )()

    monkeypatch.setattr("briefly_cli.commands.brief.extract_url", fake_extract_url)

    first = runner.invoke(app, ["https://example.com", "--extract"], color=False)
    second = runner.invoke(app, ["https://example.com", "--extract"], color=False)

    assert first.exit_code == 0
    assert second.exit_code == 0
    assert first.output == "Example\n\nCached page text.\n"
    assert second.output == first.output
    assert calls == 1


def test_summary_cache_hit_avoids_generate_brief(monkeypatch) -> None:
    calls = 0

    async def fake_generate_brief(request):
        nonlocal calls
        calls += 1
        return type("Result", (), {"text": "Cached brief."})()

    monkeypatch.setattr("briefly_cli.commands.brief.generate_brief", fake_generate_brief)

    first = runner.invoke(
        app,
        ["Source text.", "--model", "test/model", "--stream", "off"],
        color=False,
    )
    second = runner.invoke(
        app,
        ["Source text.", "--model", "test/model", "--stream", "off"],
        color=False,
    )

    assert first.exit_code == 0
    assert second.exit_code == 0
    assert first.output == "Cached brief.\n"
    assert second.output == first.output
    assert calls == 1


def test_skip_cache_bypasses_url_and_summary_cache(monkeypatch) -> None:
    async def cached_extract_url(url: str):
        return type(
            "Extracted",
            (),
            {
                "source": "https://example.com/cached",
                "title": "Cached",
                "text": "Cached page text.",
            },
        )()

    async def cached_generate_brief(request):
        return type("Result", (), {"text": "Cached brief."})()

    monkeypatch.setattr("briefly_cli.commands.brief.extract_url", cached_extract_url)
    monkeypatch.setattr("briefly_cli.commands.brief.generate_brief", cached_generate_brief)

    cached = runner.invoke(
        app,
        ["https://example.com", "--model", "test/model", "--stream", "off"],
        color=False,
    )
    assert cached.exit_code == 0

    fresh_calls = {"extract": 0, "generate": 0}

    async def fresh_extract_url(url: str):
        fresh_calls["extract"] += 1
        return type(
            "Extracted",
            (),
            {
                "source": "https://example.com/fresh",
                "title": "Fresh",
                "text": "Fresh page text.",
            },
        )()

    async def fresh_generate_brief(request):
        fresh_calls["generate"] += 1
        assert request.source == "https://example.com/fresh"
        assert request.text == "Fresh\n\nFresh page text."
        return type("Result", (), {"text": "Fresh brief."})()

    monkeypatch.setattr("briefly_cli.commands.brief.extract_url", fresh_extract_url)
    monkeypatch.setattr("briefly_cli.commands.brief.generate_brief", fresh_generate_brief)

    fresh = runner.invoke(
        app,
        ["https://example.com", "--model", "test/model", "--stream", "off", "--skip-cache"],
        color=False,
    )

    assert fresh.exit_code == 0
    assert fresh.output == "Fresh brief.\n"
    assert fresh_calls == {"extract": 1, "generate": 1}


def test_summary_cache_key_depends_on_brief_options(monkeypatch) -> None:
    calls = []

    async def fake_generate_brief(request):
        calls.append(request.options.length.preset)
        text = "Short brief." if request.options.length.preset == "short" else "Long brief."
        return type("Result", (), {"text": text})()

    monkeypatch.setattr("briefly_cli.commands.brief.generate_brief", fake_generate_brief)

    short = runner.invoke(
        app,
        ["Source text.", "--model", "test/model", "--length", "short", "--stream", "off"],
        color=False,
    )
    long = runner.invoke(
        app,
        ["Source text.", "--model", "test/model", "--length", "long", "--stream", "off"],
        color=False,
    )

    assert short.exit_code == 0
    assert long.exit_code == 0
    assert short.output == "Short brief.\n"
    assert long.output == "Long brief.\n"
    assert calls == ["short", "long"]
