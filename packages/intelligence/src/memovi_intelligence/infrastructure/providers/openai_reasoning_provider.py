from __future__ import annotations

from time import perf_counter
from typing import Any, Protocol

from memovi_intelligence.domain.entities import ReasoningResult
from memovi_intelligence.domain.exceptions import (
    InvalidPromptError,
    ReasoningProviderError,
    ReasoningProviderTimeoutError,
    ReasoningProviderUnavailableError,
)
from memovi_intelligence.domain.value_objects import Prompt, PromptRole
from memovi_intelligence.infrastructure.providers.openai_provider_settings import (
    OpenAIProviderSettings,
)

_OPENAI_ROLES = {
    PromptRole.SYSTEM.value: "system",
    PromptRole.USER.value: "user",
    "assistant": "assistant",
}


class SupportsOpenAIChatCompletions(Protocol):
    """Minimal client surface used by OpenAIReasoningProvider."""

    @property
    def chat(self) -> Any: ...


class OpenAIReasoningProvider:
    """ReasoningProvider adapter for OpenAI Chat Completions.

    Accepts provider-agnostic Prompt objects and translates them into OpenAI
    messages without leaking SDK types into the Intelligence domain.
    """

    PROVIDER_NAME = "openai"

    def __init__(
        self,
        *,
        settings: OpenAIProviderSettings,
        client: SupportsOpenAIChatCompletions | None = None,
    ) -> None:
        self._settings = settings
        self._client = client if client is not None else _build_openai_client(settings)

    @property
    def provider(self) -> str:
        return self.PROVIDER_NAME

    @property
    def model(self) -> str:
        return self._settings.model

    def reason(self, prompt: Prompt) -> ReasoningResult:
        if not prompt.citations:
            raise InvalidPromptError("Cannot reason over a prompt without citations.")

        messages = serialize_prompt_messages(prompt)
        started = perf_counter()
        try:
            response = self._client.chat.completions.create(
                model=self._settings.model,
                messages=messages,
            )
        except Exception as exc:
            raise _translate_openai_error(exc) from exc

        duration = perf_counter() - started
        answer = _extract_answer(response)
        usage = _extract_usage(response)

        return ReasoningResult.create(
            answer=answer,
            citations=prompt.citations,
            metadata={
                "query": prompt.query,
                "chunk_count": len(prompt.citations),
                "document_count": len(prompt.context.assembled_documents),
                "estimated_token_count": prompt.context.estimated_token_count,
                "model": self._settings.model,
                "prompt_tokens": usage["prompt_tokens"],
                "completion_tokens": usage["completion_tokens"],
                "total_tokens": usage["total_tokens"],
            },
            provider=self.PROVIDER_NAME,
            execution_time=duration,
            context=prompt.context,
        )


def serialize_prompt_messages(prompt: Prompt) -> list[dict[str, str]]:
    """Convert PromptMessage objects into OpenAI Chat Completions messages."""
    messages: list[dict[str, str]] = []
    for message in prompt.messages:
        role = _OPENAI_ROLES.get(message.role.value)
        if role is None:
            continue
        messages.append({"role": role, "content": message.content})
    if not messages:
        raise InvalidPromptError(
            "Prompt does not contain any OpenAI-compatible messages.",
        )
    return messages


def _build_openai_client(settings: OpenAIProviderSettings) -> SupportsOpenAIChatCompletions:
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise ReasoningProviderUnavailableError(
            "The openai package is required for OpenAIReasoningProvider.",
        ) from exc

    kwargs: dict[str, Any] = {
        "api_key": settings.api_key,
        "timeout": settings.timeout_seconds,
    }
    if settings.base_url is not None:
        kwargs["base_url"] = settings.base_url
    return OpenAI(**kwargs)


def _extract_answer(response: Any) -> str:
    try:
        choices = response.choices
        if not choices:
            raise ReasoningProviderError("OpenAI response contained no choices.")
        content = choices[0].message.content
    except (AttributeError, IndexError, TypeError) as exc:
        raise ReasoningProviderError("OpenAI response could not be parsed.") from exc

    if content is None:
        raise ReasoningProviderError("OpenAI response contained an empty answer.")
    answer = str(content).strip()
    if not answer:
        raise ReasoningProviderError("OpenAI response contained an empty answer.")
    return answer


def _extract_usage(response: Any) -> dict[str, int | None]:
    usage = getattr(response, "usage", None)
    if usage is None:
        return {
            "prompt_tokens": None,
            "completion_tokens": None,
            "total_tokens": None,
        }
    return {
        "prompt_tokens": _optional_int(getattr(usage, "prompt_tokens", None)),
        "completion_tokens": _optional_int(getattr(usage, "completion_tokens", None)),
        "total_tokens": _optional_int(getattr(usage, "total_tokens", None)),
    }


def _optional_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except TypeError, ValueError:
        return None


def _translate_openai_error(exc: Exception) -> Exception:
    if isinstance(exc, TimeoutError):
        return ReasoningProviderTimeoutError("OpenAI reasoning provider timed out.")

    try:
        import openai
    except ImportError:
        return ReasoningProviderError("OpenAI reasoning provider failed.")

    if isinstance(exc, openai.APITimeoutError):
        return ReasoningProviderTimeoutError("OpenAI reasoning provider timed out.")
    if isinstance(exc, (openai.APIConnectionError, openai.AuthenticationError)):
        return ReasoningProviderUnavailableError(
            "OpenAI reasoning provider is unavailable.",
        )
    if isinstance(exc, openai.RateLimitError):
        return ReasoningProviderUnavailableError(
            "OpenAI reasoning provider rate limit or quota exceeded.",
        )
    if isinstance(exc, openai.APIError):
        return ReasoningProviderError("OpenAI reasoning provider failed.")
    return ReasoningProviderError("OpenAI reasoning provider failed.")
