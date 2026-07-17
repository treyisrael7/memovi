import pytest
from memovi_intelligence.application import ReasoningService
from memovi_intelligence.config import IntelligenceConfig
from memovi_intelligence.domain.entities import ReasoningRequest
from memovi_intelligence.infrastructure import (
    PlaceholderKnowledgeRetriever,
    PlaceholderReasoningProvider,
)


def test_reasoning_service_initializes_with_ports_and_default_config() -> None:
    service = ReasoningService(
        knowledge_retriever=PlaceholderKnowledgeRetriever(),
        reasoning_provider=PlaceholderReasoningProvider(),
    )

    assert service.config == IntelligenceConfig()


def test_reasoning_service_accepts_explicit_config() -> None:
    config = IntelligenceConfig(default_retrieval_limit=2, max_retrieved_passages=4)
    service = ReasoningService(
        knowledge_retriever=PlaceholderKnowledgeRetriever(),
        reasoning_provider=PlaceholderReasoningProvider(),
        config=config,
    )

    assert service.config is config


def test_reasoning_service_prepare_context_is_not_implemented() -> None:
    service = ReasoningService(
        knowledge_retriever=PlaceholderKnowledgeRetriever(),
        reasoning_provider=PlaceholderReasoningProvider(),
    )
    request = ReasoningRequest.create(query="Prepare context for this question.")

    with pytest.raises(NotImplementedError, match="Knowledge retrieval"):
        service.prepare_context(request)


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
        from memovi_intelligence.domain.entities import ReasoningContext

        provider.reason(ReasoningContext.create(query=request.query))
