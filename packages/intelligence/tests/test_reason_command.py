import pytest
from memovi_intelligence.application.commands import Reason
from memovi_intelligence.application.services import ContextAssembler, ModelGateway, PromptBuilder
from memovi_intelligence.config import IntelligenceConfig
from memovi_intelligence.domain.entities import ReasoningRequest, ReasoningResult
from memovi_intelligence.domain.exceptions import (
    InvalidPromptError,
    NoRetrievedKnowledgeError,
    ReasoningProviderError,
)
from memovi_intelligence.domain.value_objects import (
    PIPELINE_STAGE_ORDER,
    Prompt,
    RetrievedKnowledge,
)
from memovi_intelligence.infrastructure import FakeReasoningProvider


class StubKnowledgeRetriever:
    def __init__(self, items: tuple[RetrievedKnowledge, ...] = ()) -> None:
        self._items = items
        self.calls = 0

    def retrieve(
        self,
        request: ReasoningRequest,
        *,
        limit: int,
    ) -> tuple[RetrievedKnowledge, ...]:
        self.calls += 1
        return self._items[:limit]


class FailingReasoningProvider:
    def reason(self, prompt: Prompt) -> ReasoningResult:
        raise RuntimeError("provider boom")


class InvalidPromptReasoningProvider:
    def reason(self, prompt: Prompt) -> ReasoningResult:
        raise InvalidPromptError("provider rejected prompt")


def _knowledge(
    *,
    chunk_id: str = "chunk-1",
    document_id: str = "doc-1",
    text: str = "Decision recorded in meeting notes.",
    score: float = 0.9,
) -> RetrievedKnowledge:
    return RetrievedKnowledge(
        chunk_id=chunk_id,
        document_id=document_id,
        text=text,
        score=score,
        document_title="Notes",
    )


def _reason(
    *,
    items: tuple[RetrievedKnowledge, ...] = (),
    provider: FakeReasoningProvider
    | FailingReasoningProvider
    | InvalidPromptReasoningProvider
    | None = None,
    config: IntelligenceConfig | None = None,
) -> tuple[Reason, StubKnowledgeRetriever]:
    retriever = StubKnowledgeRetriever(items)
    assembler = ContextAssembler(knowledge_retriever=retriever)
    resolved_config = config or IntelligenceConfig(provider="fake")
    gateway = ModelGateway(
        providers={resolved_config.provider: provider or FakeReasoningProvider()},
        config=resolved_config,
    )
    command = Reason(
        knowledge_retriever=retriever,
        context_assembler=assembler,
        model_gateway=gateway,
        prompt_builder=PromptBuilder(),
    )
    return command, retriever


def test_reason_successful_pipeline() -> None:
    item = _knowledge()
    command, retriever = _reason(items=(item,))
    request = ReasoningRequest.create(query="What was decided?")

    result = command.execute(request)

    assert isinstance(result, ReasoningResult)
    assert result.provider == "fake"
    assert result.execution_time >= 0.0
    assert result.metadata["provider"] == "fake"
    assert result.metadata["model"] == "fake-reasoning-v1"
    assert result.metadata["estimated_tokens"] == result.context.estimated_token_count
    assert "What was decided?" in result.answer
    assert "Decision recorded in meeting notes." in result.answer
    assert len(result.citations) == 1
    assert result.citations[0].chunk_id == "chunk-1"
    assert result.citations[0].document_id == "doc-1"
    assert result.metadata["chunk_count"] == 1
    assert result.metadata["section_count"] == 5
    assert result.context.retrieved_knowledge == (item,)
    assert retriever.calls == 1
    assert result.execution_trace.stage_names == PIPELINE_STAGE_ORDER
    assert result.execution_trace.metrics.retrieved_knowledge_count == 1
    assert result.execution_trace.metrics.citation_count == 1
    assert result.execution_trace.metrics.provider == "fake"


def test_reason_raises_when_retrieval_is_empty() -> None:
    command, _ = _reason(items=())
    request = ReasoningRequest.create(query="Anything known?")

    with pytest.raises(NoRetrievedKnowledgeError, match="No knowledge was retrieved"):
        command.execute(request)


def test_reason_raises_when_provider_fails() -> None:
    command, _ = _reason(items=(_knowledge(),), provider=FailingReasoningProvider())
    request = ReasoningRequest.create(query="What failed?")

    with pytest.raises(ReasoningProviderError, match="failed while producing a result"):
        command.execute(request)


def test_reason_propagates_invalid_prompt_from_provider() -> None:
    command, _ = _reason(items=(_knowledge(),), provider=InvalidPromptReasoningProvider())
    request = ReasoningRequest.create(query="Invalid prompt path")

    with pytest.raises(InvalidPromptError, match="provider rejected prompt"):
        command.execute(request)
