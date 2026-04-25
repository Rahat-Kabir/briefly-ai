from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from briefly_core.briefing import BriefingRequest


@dataclass(frozen=True)
class BriefingResult:
    text: str
    model: str


class BriefingClient(Protocol):
    async def generate(self, request: BriefingRequest) -> BriefingResult:
        pass


class LiteLlmBriefingClient:
    async def generate(self, request: BriefingRequest) -> BriefingResult:
        model = request.options.model
        if model is None:
            raise ValueError("Model is required before briefing can run.")

        import litellm

        kwargs: dict[str, Any] = {
            "model": model,
            "messages": [{"role": "user", "content": request.prompt}],
        }
        if request.options.max_output_tokens is not None:
            kwargs["max_tokens"] = request.options.max_output_tokens

        response = await litellm.acompletion(**kwargs)
        text = _response_text(response)
        if not text.strip():
            raise ValueError("Model returned an empty briefing.")

        response_model = getattr(response, "model", None) or model
        return BriefingResult(text=text.strip(), model=response_model)


async def generate_brief(
    request: BriefingRequest,
    client: BriefingClient | None = None,
) -> BriefingResult:
    active_client = client or LiteLlmBriefingClient()
    return await active_client.generate(request)


def _response_text(response: Any) -> str:
    choices = _get_value(response, "choices")
    if not choices:
        raise ValueError("Model response did not include choices.")

    message = _get_value(choices[0], "message")
    content = _get_value(message, "content")
    if not isinstance(content, str):
        raise ValueError("Model response did not include text content.")
    return content


def _get_value(value: Any, key: str) -> Any:
    if isinstance(value, dict):
        return value.get(key)
    return getattr(value, key, None)
