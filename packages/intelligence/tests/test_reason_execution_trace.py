from memovi_intelligence.application.commands import Reason
from memovi_intelligence.application.services import ContextAssembler, ModelGateway, PromptBuilder
from memovi_intelligence.config import IntelligenceConfig
from memovi_intelligence.domain.entities import ReasoningRequest
from memovi_intelligence.domain.value_objects import (
    PIPELINE_STAGE_ORDER,
    ExecutionStage,
    RetrievedKnowledge,
)
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


def test_reason_pipeline_records_every_execution_stage() -> None:
    items = (
        _knowledge(chunk_id="chunk-1", document_id="doc-1", score=0.95),
        _knowledge(
            chunk_id="chunk-2",
            document_id="doc-2",
            text="Follow-up action assigned.",
            score=0.85,
        ),
    )
    retriever = StubKnowledgeRetriever(items)
    config = IntelligenceConfig(provider="fake")
    command = Reason(
        knowledge_retriever=retriever,
        context_assembler=ContextAssembler(knowledge_retriever=retriever),
        model_gateway=ModelGateway(
            providers={"fake": FakeReasoningProvider()},
            config=config,
        ),
        prompt_builder=PromptBuilder(),
    )

    result = command.execute(ReasoningRequest.create(query="What was decided?"))
    trace = result.execution_trace

    assert trace.stage_names == PIPELINE_STAGE_ORDER
    assert [timing.stage.value for timing in trace.stages] == [
        "retrieval",
        "context_assembly",
        "prompt_build",
        "provider_resolution",
        "model_execution",
    ]
    for timing in trace.stages:
        assert timing.finished_at >= timing.started_at
        assert timing.duration >= 0.0

    assert trace.metrics.provider == "fake"
    assert trace.metrics.model == "fake-reasoning-v1"
    assert trace.metrics.estimated_input_tokens == result.context.estimated_token_count
    assert trace.metrics.output_tokens is None
    assert trace.metrics.retrieved_knowledge_count == 2
    assert trace.metrics.document_count == 2
    assert trace.metrics.citation_count == 2
    assert result.execution_time == trace.total_duration
    duration = result.metadata["duration"]
    assert isinstance(duration, float)
    assert result.execution_time >= duration

    model_stage = trace.timing_for(ExecutionStage.MODEL_EXECUTION)
    assert model_stage is not None
    assert model_stage.duration >= 0.0
