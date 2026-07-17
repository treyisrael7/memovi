import pytest
from memovi_intelligence.application import ContextAssembler, ReasoningService
from memovi_intelligence.config import IntelligenceConfig
from memovi_intelligence.domain.entities import ReasoningContext, ReasoningRequest
from memovi_intelligence.domain.value_objects import RetrievedKnowledge
from memovi_intelligence.infrastructure import (
    PlaceholderKnowledgeRetriever,
    PlaceholderReasoningProvider,
)


class FakeKnowledgeRetriever:
    def __init__(self, items: tuple[RetrievedKnowledge, ...] = ()) -> None:
        self._items = items

    def retrieve(
        self,
        request: ReasoningRequest,
        *,
        limit: int,
    ) -> tuple[RetrievedKnowledge, ...]:
        return self._items[:limit]


def test_reasoning_service_initializes_with_ports_and_default_config() -> None:
    service = ReasoningService(
        knowledge_retriever=PlaceholderKnowledgeRetriever(),
        reasoning_provider=PlaceholderReasoningProvider(),
    )

    assert service.config == IntelligenceConfig()


def test_reasoning_service_accepts_explicit_config() -> None:
    config = IntelligenceConfig(default_retrieval_limit=2, max_chunks=4)
    service = ReasoningService(
        knowledge_retriever=PlaceholderKnowledgeRetriever(),
        reasoning_provider=PlaceholderReasoningProvider(),
        config=config,
    )

    assert service.config is config


def test_reasoning_service_prepare_context_uses_assembler() -> None:
    item = RetrievedKnowledge(
        chunk_id="chunk-1",
        document_id="doc-1",
        text="Assembled via service.",
        score=0.7,
    )
    service = ReasoningService(
        knowledge_retriever=FakeKnowledgeRetriever((item,)),
        reasoning_provider=PlaceholderReasoningProvider(),
    )
    request = ReasoningRequest.create(query="Prepare context for this question.")

    context = service.prepare_context(request)

    assert isinstance(context, ReasoningContext)
    assert context.retrieved_knowledge == (item,)
    assert context.request is request


def test_reasoning_service_reason_is_not_implemented() -> None:
    service = ReasoningService(
        knowledge_retriever=PlaceholderKnowledgeRetriever(),
        reasoning_provider=PlaceholderReasoningProvider(),
    )
    request = ReasoningRequest.create(query="Reason about this question.")

    with pytest.raises(NotImplementedError, match="Reasoning workflows"):
        service.reason(request)


def test_placeholder_adapters_raise_not_implemented() -> None:
    request = ReasoningRequest.create(query="Adapter placeholder behavior.")
    retriever = PlaceholderKnowledgeRetriever()
    provider = PlaceholderReasoningProvider()

    with pytest.raises(NotImplementedError, match="Search"):
        retriever.retrieve(request, limit=3)

    with pytest.raises(NotImplementedError, match="provider"):
        provider.reason(ReasoningContext.empty(request))


def test_context_assembler_is_exported() -> None:
    assert ContextAssembler is not None
