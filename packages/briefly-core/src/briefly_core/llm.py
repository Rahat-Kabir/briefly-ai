from __future__ import annotations

from dataclasses import dataclass
from typing import Any, AsyncIterator, Protocol

from briefly_core.briefing import BriefingRequest


@dataclass(frozen=True)
class BriefingResult:
    text: str
    model: str


class BriefingClient(Protocol):
    async def generate(self, request: BriefingRequest) -> BriefingResult: ...

    def stream(self, request: BriefingRequest) -> AsyncIterator[str]: ...


class LiteLlmBriefingClient:
    async def generate(self, request: BriefingRequest) -> BriefingResult:
        model = _require_model(request)

        import litellm

        response = await litellm.acompletion(**_completion_kwargs(request, model))
        text = _response_text(response)
        if not text.strip():
            raise ValueError("Model returned an empty briefing.")

        response_model = getattr(response, "model", None) or model
        return BriefingResult(text=text.strip(), model=response_model)

    async def stream(self, request: BriefingRequest) -> AsyncIterator[str]:
        model = _require_model(request)

        import litellm

        kwargs = _completion_kwargs(request, model)
        kwargs["stream"] = True

        response: Any = await litellm.acompletion(**kwargs)
        emitted = False
        async for chunk in response:
            text = _chunk_text(chunk)
            if text:
                emitted = True
                yield text

        if not emitted:
            raise ValueError("Model returned an empty briefing.")


async def generate_brief(
    request: BriefingRequest,
    client: BriefingClient | None = None,
) -> BriefingResult:
    active_client = client or LiteLlmBriefingClient()
    return await active_client.generate(request)


async def generate_brief_stream(
    request: BriefingRequest,
    client: BriefingClient | None = None,
) -> AsyncIterator[str]:
    active_client = client or LiteLlmBriefingClient()
    async for chunk in active_client.stream(request):
        yield chunk


def _require_model(request: BriefingRequest) -> str:
    model = request.options.model
    if model is None:
        raise ValueError("Model is required before briefing can run.")
    return model


def _completion_kwargs(request: BriefingRequest, model: str) -> dict[str, Any]:
    kwargs: dict[str, Any] = {
        "model": model,
        "messages": [{"role": "user", "content": request.prompt}],
    }
    if request.options.max_output_tokens is not None:
        kwargs["max_tokens"] = request.options.max_output_tokens
    return kwargs


def _response_text(response: Any) -> str:
    choices = _get_value(response, "choices")
    if not choices:
        raise ValueError("Model response did not include choices.")

    message = _get_value(choices[0], "message")
    content = _get_value(message, "content")
    if not isinstance(content, str):
        raise ValueError("Model response did not include text content.")
    return content


def _chunk_text(chunk: Any) -> str:
    choices = _get_value(chunk, "choices")
    if not choices:
        return ""

    delta = _get_value(choices[0], "delta")
    if delta is None:
        return ""

    content = _get_value(delta, "content")
    if not isinstance(content, str):
        return ""
    return content


def _get_value(value: Any, key: str) -> Any:
    if isinstance(value, dict):
        return value.get(key)
    return getattr(value, key, None)
