from dataclasses import dataclass

from memovi_intelligence.domain.exceptions import InvalidExecutionTraceError
from memovi_intelligence.domain.value_objects.execution_metrics import ExecutionMetrics
from memovi_intelligence.domain.value_objects.execution_stage import (
    PIPELINE_STAGE_ORDER,
    ExecutionStage,
)
from memovi_intelligence.domain.value_objects.stage_timing import StageTiming


@dataclass(frozen=True, slots=True)
class ExecutionTrace:
    """Immutable structured execution metadata for a reasoning request."""

    stages: tuple[StageTiming, ...]
    metrics: ExecutionMetrics

    def __post_init__(self) -> None:
        if any(not isinstance(stage, StageTiming) for stage in self.stages):
            raise InvalidExecutionTraceError(
                "stages must contain StageTiming instances.",
            )
        if not isinstance(self.metrics, ExecutionMetrics):
            raise InvalidExecutionTraceError("metrics must be an ExecutionMetrics.")

        object.__setattr__(self, "stages", tuple(self.stages))

        names = tuple(timing.stage for timing in self.stages)
        if len(names) != len(set(names)):
            raise InvalidExecutionTraceError("stages must not contain duplicates.")
        if names and names != PIPELINE_STAGE_ORDER[: len(names)]:
            raise InvalidExecutionTraceError(
                "stages must appear in pipeline order: "
                + ", ".join(stage.value for stage in PIPELINE_STAGE_ORDER)
                + ".",
            )

    @property
    def stage_names(self) -> tuple[ExecutionStage, ...]:
        return tuple(timing.stage for timing in self.stages)

    def timing_for(self, stage: ExecutionStage) -> StageTiming | None:
        for timing in self.stages:
            if timing.stage is stage:
                return timing
        return None

    @property
    def total_duration(self) -> float:
        return sum(timing.duration for timing in self.stages)
