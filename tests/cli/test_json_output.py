import json

from click.testing import CliRunner
import pytest

from briefly_cli.main import app
from briefly_core.llm import BriefingResult

runner = CliRunner()


def test_extract_json_outputs_structured_literal_text() -> None:
    result = runner.invoke(app, ["Briefly reads text.", "--extract", "--json"], color=False)

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["input"] == {
        "kind": "text",
        "source": "literal",
        "format": "text",
        "length": {"kind": "preset", "preset": "medium"},
        "maxInputChars": None,
        "maxOutputTokens": None,
        "model": None,
    }
    assert payload["extracted"] == {
        "kind": "text",
        "source": "literal",
        "text": "Briefly reads text.",
    }
    assert payload["prompt"] is None
    assert payload["llm"] is None
    assert payload["cache"] == {"enabled": True}
    assert payload["summary"] is None


def test_extract_json_outputs_structured_url_text(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_extract_url(url: str, **kwargs):
        assert url == "https://example.com"
        assert kwargs["output_format"] == "markdown"
        return type(
            "Extracted",
            (),
            {
                "source": "https://example.com/final",
                "title": "Example Domain",
                "text": "# Heading\n\nPage text.",
            },
        )()

    monkeypatch.setattr("briefly_cli.commands.brief.extract_url", fake_extract_url)

    result = runner.invoke(
        app,
        ["https://example.com", "--extract", "--json", "--output-format", "markdown"],
        color=False,
    )

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["input"]["kind"] == "url"
    assert payload["input"]["source"] == "https://example.com"
    assert payload["input"]["format"] == "markdown"
    assert payload["extracted"] == {
        "kind": "url",
        "source": "https://example.com/final",
        "text": "Example Domain\n\n# Heading\n\nPage text.",
    }
    assert payload["summary"] is None


def test_brief_json_outputs_prompt_llm_summary_and_cache_status(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_generate_brief(request):
        assert request.options.model == "test/model"
        return BriefingResult(text="Whole brief.", model="provider/model")

    monkeypatch.setattr("briefly_cli.commands.brief.generate_brief", fake_generate_brief)

    result = runner.invoke(
        app,
        ["Source text.", "--model", "test/model", "--stream", "off", "--json"],
        color=False,
    )

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["input"]["kind"] == "text"
    assert payload["input"]["source"] == "literal"
    assert payload["input"]["model"] == "test/model"
    assert payload["extracted"]["text"] == "Source text."
    assert "Source text." in payload["prompt"]
    assert payload["llm"] == {"model": "provider/model"}
    assert payload["cache"] == {"enabled": True, "summaryHit": False}
    assert payload["summary"] == "Whole brief."


def test_brief_json_cache_hit_avoids_generate_brief(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = 0

    async def fake_generate_brief(request):
        nonlocal calls
        calls += 1
        return BriefingResult(text="Cached brief.", model="provider/model")

    monkeypatch.setattr("briefly_cli.commands.brief.generate_brief", fake_generate_brief)

    first = runner.invoke(
        app,
        ["Source text.", "--model", "test/model", "--stream", "off", "--json"],
        color=False,
    )
    second = runner.invoke(
        app,
        ["Source text.", "--model", "test/model", "--stream", "off", "--json"],
        color=False,
    )

    assert first.exit_code == 0
    assert second.exit_code == 0
    first_payload = json.loads(first.output)
    second_payload = json.loads(second.output)
    assert calls == 1
    assert first_payload["cache"] == {"enabled": True, "summaryHit": False}
    assert second_payload["cache"] == {"enabled": True, "summaryHit": True}
    assert second_payload["llm"] == {"model": "test/model"}
    assert second_payload["summary"] == "Cached brief."


def test_brief_json_disables_streaming(monkeypatch: pytest.MonkeyPatch) -> None:
    streamed = []

    async def fake_generate_brief_stream(request, client=None):
        streamed.append(request)
        yield "should not run"

    async def fake_generate_brief(request):
        return BriefingResult(text="Whole brief.", model="provider/model")

    monkeypatch.setattr(
        "briefly_cli.commands.brief.generate_brief_stream", fake_generate_brief_stream
    )
    monkeypatch.setattr("briefly_cli.commands.brief.generate_brief", fake_generate_brief)

    result = runner.invoke(
        app,
        ["Source text.", "--model", "test/model", "--stream", "on", "--json"],
        color=False,
    )

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert streamed == []
    assert payload["summary"] == "Whole brief."
