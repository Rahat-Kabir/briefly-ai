import asyncio
from types import SimpleNamespace

import pytest

from briefly_core.briefing import BriefingOptions, build_briefing_request
from briefly_core.flags import LengthArg
from briefly_core.input import ResolvedInput
from briefly_core.llm import BriefingResult, LiteLlmBriefingClient, generate_brief


def _request(model: str | None = "test/model", max_output_tokens: int | None = None):
    return build_briefing_request(
        ResolvedInput(kind="text", source="literal", text="Brief this."),
        BriefingOptions(
            length=LengthArg(kind="preset", preset="short"),
            output_format="text",
            model=model,
            max_output_tokens=max_output_tokens,
        ),
    )


def test_generate_brief_uses_injected_client() -> None:
    class FakeClient:
        async def generate(self, request):
            assert request.text == "Brief this."
            return BriefingResult(text="Fake brief.", model="fake/model")

    result = asyncio.run(generate_brief(_request(), FakeClient()))

    assert result == BriefingResult(text="Fake brief.", model="fake/model")


def test_litellm_client_requires_model() -> None:
    with pytest.raises(ValueError, match="Model is required"):
        asyncio.run(LiteLlmBriefingClient().generate(_request(model=None)))


def test_litellm_client_forwards_request(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = []

    async def fake_acompletion(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(
            model="provider/model",
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(content=" Real brief. "),
                )
            ],
        )

    import litellm

    monkeypatch.setattr(litellm, "acompletion", fake_acompletion)

    result = asyncio.run(LiteLlmBriefingClient().generate(_request(max_output_tokens=123)))

    assert result == BriefingResult(text="Real brief.", model="provider/model")
    assert calls[0]["model"] == "test/model"
    assert calls[0]["max_tokens"] == 123
    assert calls[0]["messages"][0]["role"] == "user"
    assert "Brief this." in calls[0]["messages"][0]["content"]


def test_litellm_client_forwards_default_token_cap(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = []

    async def fake_acompletion(**kwargs):
        calls.append(kwargs)
        return {"model": "provider/model", "choices": [{"message": {"content": "Brief."}}]}

    import litellm

    monkeypatch.setattr(litellm, "acompletion", fake_acompletion)

    result = asyncio.run(LiteLlmBriefingClient().generate(_request()))

    assert result == BriefingResult(text="Brief.", model="test/model")
    assert calls[0]["max_tokens"] == 120


def test_litellm_client_rejects_empty_response(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_acompletion(**kwargs):
        return {"choices": [{"message": {"content": "   "}}]}

    import litellm

    monkeypatch.setattr(litellm, "acompletion", fake_acompletion)

    with pytest.raises(ValueError, match="empty briefing"):
        asyncio.run(LiteLlmBriefingClient().generate(_request()))
