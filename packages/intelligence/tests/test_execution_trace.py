from dataclasses import FrozenInstanceError
from datetime import UTC, datetime, timedelta

import pytest
from memovi_intelligence.domain.exceptions import InvalidExecutionTraceError
from memovi_intelligence.domain.value_objects import (
    PIPELINE_STAGE_ORDER,
    ExecutionMetrics,
    ExecutionStage,
    ExecutionTrace,
    StageTiming,
)


def _timing(
    stage: ExecutionStage,
    *,
    started_offset: float = 0.0,
    duration: float = 0.01,
) -> StageTiming:
    started_at = datetime(2026, 7, 17, 12, 0, 0, tzinfo=UTC) + timedelta(
        seconds=started_offset,
    )
    return StageTiming(
        stage=stage,
        started_at=started_at,
        finished_at=started_at + timedelta(seconds=duration),
        duration=duration,
    )


def _metrics(**overrides: object) -> ExecutionMetrics:
    values: dict[str, object] = {
        "provider": "fake",
        "model": "fake-reasoning-v1",
        "estimated_input_tokens": 42,
        "output_tokens": None,
        "retrieved_knowledge_count": 2,
        "document_count": 1,
        "citation_count": 2,
    }
    values.update(overrides)
    return ExecutionMetrics(**values)  # type: ignore[arg-type]


def test_execution_stage_pipeline_order() -> None:
    assert PIPELINE_STAGE_ORDER == (
        ExecutionStage.RETRIEVAL,
        ExecutionStage.CONTEXT_ASSEMBLY,
        ExecutionStage.PROMPT_BUILD,
        ExecutionStage.PROVIDER_RESOLUTION,
        ExecutionStage.MODEL_EXECUTION,
    )
    assert tuple(stage.value for stage in PIPELINE_STAGE_ORDER) == (
        "retrieval",
        "context_assembly",
        "prompt_build",
        "provider_resolution",
        "model_execution",
    )


def test_stage_timing_records_duration() -> None:
    started = datetime(2026, 7, 17, 12, 0, 0, tzinfo=UTC)
    finished = started + timedelta(milliseconds=25)
    timing = StageTiming(
        stage=ExecutionStage.RETRIEVAL,
        started_at=started,
        finished_at=finished,
        duration=0.025,
    )

    assert timing.stage is ExecutionStage.RETRIEVAL
    assert timing.started_at == started
    assert timing.finished_at == finished
    assert timing.duration == 0.025


def test_stage_timing_rejects_negative_duration() -> None:
    started = datetime(2026, 7, 17, 12, 0, 0, tzinfo=UTC)
    with pytest.raises(InvalidExecutionTraceError, match="duration cannot be negative"):
        StageTiming(
            stage=ExecutionStage.RETRIEVAL,
            started_at=started,
            finished_at=started,
            duration=-0.1,
        )


def test_execution_metrics_population() -> None:
    metrics = ExecutionMetrics(
        provider=" openai ",
        model=" gpt-4.1-mini ",
        estimated_input_tokens=100,
        output_tokens=50,
        retrieved_knowledge_count=3,
        document_count=2,
        citation_count=3,
    )

    assert metrics.provider == "openai"
    assert metrics.model == "gpt-4.1-mini"
    assert metrics.estimated_input_tokens == 100
    assert metrics.output_tokens == 50
    assert metrics.retrieved_knowledge_count == 3
    assert metrics.document_count == 2
    assert metrics.citation_count == 3


def test_execution_metrics_rejects_blank_provider() -> None:
    with pytest.raises(InvalidExecutionTraceError, match="provider is required"):
        ExecutionMetrics(
            provider="  ",
            model="fake-reasoning-v1",
            estimated_input_tokens=0,
            output_tokens=None,
            retrieved_knowledge_count=0,
            document_count=0,
            citation_count=0,
        )


def test_execution_trace_accepts_full_pipeline_order() -> None:
    stages = tuple(
        _timing(stage, started_offset=index * 0.01, duration=0.01)
        for index, stage in enumerate(PIPELINE_STAGE_ORDER)
    )
    trace = ExecutionTrace(stages=stages, metrics=_metrics())

    assert trace.stage_names == PIPELINE_STAGE_ORDER
    assert trace.total_duration == pytest.approx(0.05)
    assert trace.timing_for(ExecutionStage.PROMPT_BUILD) is stages[2]


def test_execution_trace_rejects_out_of_order_stages() -> None:
    with pytest.raises(InvalidExecutionTraceError, match="pipeline order"):
        ExecutionTrace(
            stages=(
                _timing(ExecutionStage.CONTEXT_ASSEMBLY),
                _timing(ExecutionStage.RETRIEVAL, started_offset=0.01),
            ),
            metrics=_metrics(),
        )


def test_execution_trace_rejects_duplicate_stages() -> None:
    with pytest.raises(InvalidExecutionTraceError, match="duplicates"):
        ExecutionTrace(
            stages=(
                _timing(ExecutionStage.RETRIEVAL),
                _timing(ExecutionStage.RETRIEVAL, started_offset=0.01),
            ),
            metrics=_metrics(),
        )


def test_execution_trace_is_immutable() -> None:
    trace = ExecutionTrace(
        stages=(_timing(ExecutionStage.RETRIEVAL),),
        metrics=_metrics(),
    )

    with pytest.raises(FrozenInstanceError):
        trace.metrics = _metrics(provider="openai")  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        trace.stages[0].duration = 1.0  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        trace.metrics.citation_count = 99  # type: ignore[misc]
