from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from memovi_intelligence.application.services import ContextAssembler, PromptBuilder
from memovi_intelligence.config import IntelligenceConfig
from memovi_intelligence.domain.entities import ReasoningRequest, ReasoningResult
from memovi_intelligence.domain.exceptions import (
    ReasoningProviderError,
    ReasoningProviderTimeoutError,
    ReasoningProviderUnavailableError,
)
from memovi_intelligence.domain.value_objects import Prompt, RetrievedKnowledge
from memovi_intelligence.infrastructure import (
    OpenAIProviderSettings,
    OpenAIReasoningProvider,
    serialize_prompt_messages,
)


class StubKnowledgeRetriever:
    def __init__(self, items: tuple[RetrievedKnowledge, ...] = ()) -> None:
        self._items = items

    def retrieve(
        self,
        request: ReasoningRequest,
        *,
        limit: int,
    ) -> tuple[RetrievedKnowledge, ...]:
        return self._items[:limit]


def _prompt() -> Prompt:
    item = RetrievedKnowledge(
        chunk_id="chunk-memovi",
        document_id="doc-memovi",
        text="Memovi is a self-hosted knowledge platform.",
        score=0.95,
        document_title="Memovi",
    )
    request = ReasoningRequest.create(query="What is Memovi?")
    context = ContextAssembler(
        knowledge_retriever=StubKnowledgeRetriever((item,)),
    ).assemble(request)
    return PromptBuilder().build(context)


def _settings(*, model: str = "gpt-4o-mini") -> OpenAIProviderSettings:
    return OpenAIProviderSettings(api_key="test-key", model=model)


def _mock_response(
    *,
    content: str = "Memovi is a self-hosted knowledge platform.",
    prompt_tokens: int = 12,
    completion_tokens: int = 8,
    total_tokens: int = 20,
) -> SimpleNamespace:
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=content))],
        usage=SimpleNamespace(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
        ),
    )


def test_serialize_prompt_messages_maps_system_and_user() -> None:
    prompt = _prompt()

    messages = serialize_prompt_messages(prompt)

    assert messages == [
        {"role": "system", "content": prompt.messages[0].content},
        {"role": "user", "content": prompt.messages[1].content},
    ]
    assert all(message["role"] in {"system", "user", "assistant"} for message in messages)


def test_openai_settings_from_config_uses_configured_model() -> None:
    config = IntelligenceConfig(provider="openai", model="gpt-4.1-mini")

    settings = OpenAIProviderSettings.from_config(config, api_key="from-arg")

    assert settings.model == "gpt-4.1-mini"
    assert settings.api_key == "from-arg"


def test_openai_settings_from_config_requires_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    config = IntelligenceConfig(provider="openai")

    with pytest.raises(ReasoningProviderUnavailableError, match="API key"):
        OpenAIProviderSettings.from_config(config)


def test_openai_provider_parses_response_and_tokens() -> None:
    prompt = _prompt()
    client = MagicMock()
    client.chat.completions.create.return_value = _mock_response()
    provider = OpenAIReasoningProvider(settings=_settings(), client=client)

    result = provider.reason(prompt)

    assert isinstance(result, ReasoningResult)
    assert result.provider == "openai"
    assert result.answer == "Memovi is a self-hosted knowledge platform."
    assert result.citations == prompt.citations
    assert result.context is prompt.context
    assert result.execution_time >= 0.0
    assert result.metadata["model"] == "gpt-4o-mini"
    assert result.metadata["prompt_tokens"] == 12
    assert result.metadata["completion_tokens"] == 8
    assert result.metadata["total_tokens"] == 20

    client.chat.completions.create.assert_called_once()
    call_kwargs = client.chat.completions.create.call_args.kwargs
    assert call_kwargs["model"] == "gpt-4o-mini"
    assert call_kwargs["messages"] == serialize_prompt_messages(prompt)


def test_openai_provider_handles_missing_usage() -> None:
    prompt = _prompt()
    client = MagicMock()
    client.chat.completions.create.return_value = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content="Answer"))],
        usage=None,
    )
    provider = OpenAIReasoningProvider(settings=_settings(), client=client)

    result = provider.reason(prompt)

    assert result.metadata["prompt_tokens"] is None
    assert result.metadata["completion_tokens"] is None
    assert result.metadata["total_tokens"] is None


def test_openai_provider_translates_timeout() -> None:
    openai = pytest.importorskip("openai")
    prompt = _prompt()
    client = MagicMock()
    client.chat.completions.create.side_effect = openai.APITimeoutError(request=MagicMock())
    provider = OpenAIReasoningProvider(settings=_settings(), client=client)

    with pytest.raises(ReasoningProviderTimeoutError, match="timed out"):
        provider.reason(prompt)


def test_openai_provider_translates_connection_error() -> None:
    openai = pytest.importorskip("openai")
    prompt = _prompt()
    client = MagicMock()
    client.chat.completions.create.side_effect = openai.APIConnectionError(request=MagicMock())
    provider = OpenAIReasoningProvider(settings=_settings(), client=client)

    with pytest.raises(ReasoningProviderUnavailableError, match="unavailable"):
        provider.reason(prompt)


def test_openai_provider_translates_rate_limit() -> None:
    openai = pytest.importorskip("openai")
    prompt = _prompt()
    client = MagicMock()
    client.chat.completions.create.side_effect = openai.RateLimitError(
        message="quota",
        response=MagicMock(status_code=429, headers={}),
        body=None,
    )
    provider = OpenAIReasoningProvider(settings=_settings(), client=client)

    with pytest.raises(ReasoningProviderUnavailableError, match="rate limit or quota"):
        provider.reason(prompt)


def test_openai_provider_translates_generic_api_error() -> None:
    openai = pytest.importorskip("openai")
    prompt = _prompt()
    client = MagicMock()
    client.chat.completions.create.side_effect = openai.APIError(
        message="boom",
        request=MagicMock(),
        body=None,
    )
    provider = OpenAIReasoningProvider(settings=_settings(), client=client)

    with pytest.raises(ReasoningProviderError, match="failed") as exc_info:
        provider.reason(prompt)

    assert isinstance(exc_info.value, ReasoningProviderError)
    assert isinstance(exc_info.value.__cause__, openai.APIError)


def test_openai_provider_rejects_empty_answer() -> None:
    prompt = _prompt()
    client = MagicMock()
    client.chat.completions.create.return_value = _mock_response(content="   ")
    provider = OpenAIReasoningProvider(settings=_settings(), client=client)

    with pytest.raises(ReasoningProviderError, match="empty answer"):
        provider.reason(prompt)
