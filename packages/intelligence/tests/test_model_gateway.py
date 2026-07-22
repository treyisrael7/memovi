import pytest
from memovi_intelligence.application.services import ContextAssembler, ModelGateway, PromptBuilder
from memovi_intelligence.config import IntelligenceConfig, ReasoningProviderKind
from memovi_intelligence.domain.entities import ReasoningRequest, ReasoningResult
from memovi_intelligence.domain.exceptions import (
    ReasoningProviderError,
    ReasoningProviderTimeoutError,
    ReasoningProviderUnavailableError,
    UnknownReasoningProviderError,
)
from memovi_intelligence.domain.value_objects import Prompt, RetrievedKnowledge
from memovi_intelligence.infrastructure import FakeReasoningProvider


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


class FailingReasoningProvider:
    def reason(self, prompt: Prompt) -> ReasoningResult:
        raise RuntimeError("provider boom")


class TimeoutReasoningProvider:
    def reason(self, prompt: Prompt) -> ReasoningResult:
        raise TimeoutError("took too long")


def _prompt() -> Prompt:
    item = RetrievedKnowledge(
        chunk_id="chunk-1",
        document_id="doc-1",
        text="Memovi is a self-hosted knowledge platform.",
        score=0.9,
        document_title="Memovi",
    )
    request = ReasoningRequest.create(query="What is Memovi?")
    context = ContextAssembler(
        knowledge_retriever=StubKnowledgeRetriever((item,)),
    ).assemble(request)
    return PromptBuilder().build(context)


def test_model_gateway_selects_configured_fake_provider() -> None:
    prompt = _prompt()
    gateway = ModelGateway(
        providers={ReasoningProviderKind.FAKE.value: FakeReasoningProvider()},
        config=IntelligenceConfig(provider="fake"),
    )

    result = gateway.execute(prompt)

    assert result.provider == "fake"
    assert result.metadata["provider"] == "fake"
    assert result.metadata["model"] == "fake-reasoning-v1"
    assert result.metadata["estimated_tokens"] == prompt.context.estimated_token_count
    assert isinstance(result.metadata["duration"], float)
    assert result.metadata["duration"] >= 0.0
    assert result.execution_time == result.metadata["duration"]
    assert "What is Memovi?" in result.answer


def test_model_gateway_rejects_unknown_provider() -> None:
    gateway = ModelGateway(
        providers={ReasoningProviderKind.FAKE.value: FakeReasoningProvider()},
        config=IntelligenceConfig(provider="not-a-provider"),
    )

    with pytest.raises(UnknownReasoningProviderError, match="Unknown reasoning provider"):
        gateway.execute(_prompt())


def test_model_gateway_rejects_unavailable_provider() -> None:
    gateway = ModelGateway(
        providers={ReasoningProviderKind.FAKE.value: FakeReasoningProvider()},
        config=IntelligenceConfig(provider="openai"),
    )

    with pytest.raises(
        ReasoningProviderUnavailableError,
        match="Reasoning provider 'openai' is not available",
    ):
        gateway.execute(_prompt())


def test_model_gateway_maps_provider_failure() -> None:
    gateway = ModelGateway(
        providers={ReasoningProviderKind.FAKE.value: FailingReasoningProvider()},
        config=IntelligenceConfig(provider="fake"),
    )

    with pytest.raises(ReasoningProviderError, match="failed while producing a result"):
        gateway.execute(_prompt())


def test_model_gateway_maps_timeout() -> None:
    gateway = ModelGateway(
        providers={ReasoningProviderKind.FAKE.value: TimeoutReasoningProvider()},
        config=IntelligenceConfig(provider="fake"),
    )

    with pytest.raises(ReasoningProviderTimeoutError, match="timed out"):
        gateway.execute(_prompt())


def test_model_gateway_uses_configured_model_metadata() -> None:
    gateway = ModelGateway(
        providers={ReasoningProviderKind.FAKE.value: FakeReasoningProvider()},
        config=IntelligenceConfig(provider="fake", model="custom-fake-model"),
    )

    result = gateway.execute(_prompt())

    assert result.metadata["model"] == "custom-fake-model"
    assert gateway.model == "custom-fake-model"


def test_what_is_memovi_reason_uses_gateway_not_provider_directly() -> None:
    from memovi_intelligence.application.commands import Reason
    from memovi_intelligence.application.ports import ReasoningProvider

    knowledge = (
        RetrievedKnowledge(
            chunk_id="chunk-memovi",
            document_id="doc-memovi",
            text="Memovi is a self-hosted knowledge platform.",
            score=0.95,
            document_title="Memovi",
        ),
        RetrievedKnowledge(
            chunk_id="chunk-knowledge",
            document_id="doc-principles",
            text="Knowledge is the product.",
            score=0.90,
            document_title="Principles",
        ),
        RetrievedKnowledge(
            chunk_id="chunk-ai",
            document_id="doc-principles",
            text="AI is a consumer.",
            score=0.85,
            document_title="Principles",
        ),
    )

    class RecordingFakeProvider(FakeReasoningProvider):
        def __init__(self) -> None:
            self.calls = 0

        def reason(self, prompt: Prompt, *, model: str | None = None) -> ReasoningResult:
            self.calls += 1
            return super().reason(prompt, model=model)

    class RecordingGateway(ModelGateway):
        def __init__(self, **kwargs: object) -> None:
            super().__init__(**kwargs)  # type: ignore[arg-type]
            self.execute_calls = 0
            self.resolve_calls = 0

        def resolve_provider(self, provider_name: str | None = None) -> ReasoningProvider:
            self.resolve_calls += 1
            return super().resolve_provider(provider_name)

        def execute(
            self,
            prompt: Prompt,
            *,
            provider: ReasoningProvider | None = None,
            provider_name: str | None = None,
            model: str | None = None,
        ) -> ReasoningResult:
            self.execute_calls += 1
            return super().execute(
                prompt,
                provider=provider,
                provider_name=provider_name,
                model=model,
            )

    provider = RecordingFakeProvider()
    gateway = RecordingGateway(
        providers={"fake": provider},
        config=IntelligenceConfig(provider="fake"),
    )
    retriever = StubKnowledgeRetriever(knowledge)
    command = Reason(
        knowledge_retriever=retriever,
        context_assembler=ContextAssembler(knowledge_retriever=retriever),
        model_gateway=gateway,
        prompt_builder=PromptBuilder(),
    )

    assert not hasattr(command, "_reasoning_provider")
    assert isinstance(command._model_gateway, ModelGateway)
    assert ReasoningProvider not in getattr(command, "__annotations__", {})

    result = command.execute(ReasoningRequest.create(query="What is Memovi?"))

    assert gateway.resolve_calls == 1
    assert gateway.execute_calls == 1
    assert provider.calls == 1
    assert result.provider == "fake"
    assert result.metadata["provider"] == "fake"
    assert result.metadata["model"] == "fake-reasoning-v1"
    assert isinstance(result.metadata["duration"], float)
    assert result.metadata["duration"] >= 0.0
    assert result.execution_time >= result.metadata["duration"]
    assert result.execution_time == result.execution_trace.total_duration
    assert result.metadata["estimated_tokens"] == result.context.estimated_token_count
    assert result.metadata["estimated_tokens"] > 0
    assert "What is Memovi?" in result.answer
    assert "Memovi is a self-hosted knowledge platform." in result.answer
    assert len(result.execution_trace.stages) == 5
    assert result.execution_trace.metrics.document_count == 2
    assert result.execution_trace.metrics.retrieved_knowledge_count == 3
    assert result.execution_trace.metrics.citation_count == 3
