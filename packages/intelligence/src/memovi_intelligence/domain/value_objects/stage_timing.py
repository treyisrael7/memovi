from dataclasses import dataclass
from datetime import datetime

from memovi_intelligence.domain.exceptions import InvalidExecutionTraceError
from memovi_intelligence.domain.value_objects.execution_stage import ExecutionStage


@dataclass(frozen=True, slots=True)
class StageTiming:
    """Immutable wall-clock timing for a single execution stage."""

    stage: ExecutionStage
    started_at: datetime
    finished_at: datetime
    duration: float

    def __post_init__(self) -> None:
        if not isinstance(self.stage, ExecutionStage):
            raise InvalidExecutionTraceError("stage must be an ExecutionStage.")
        if not isinstance(self.started_at, datetime):
            raise InvalidExecutionTraceError("started_at must be a datetime.")
        if not isinstance(self.finished_at, datetime):
            raise InvalidExecutionTraceError("finished_at must be a datetime.")
        if self.finished_at < self.started_at:
            raise InvalidExecutionTraceError(
                "finished_at cannot be earlier than started_at.",
            )
        if self.duration < 0:
            raise InvalidExecutionTraceError("duration cannot be negative.")
