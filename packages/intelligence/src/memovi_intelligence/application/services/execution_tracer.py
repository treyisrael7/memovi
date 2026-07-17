from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from time import perf_counter

from memovi_intelligence.domain.value_objects import (
    ExecutionMetrics,
    ExecutionStage,
    ExecutionTrace,
    StageTiming,
)


class ExecutionTracer:
    """Records stage timings for a single Reason pipeline execution.

    Builds an immutable ExecutionTrace when complete. Timing lives here — not in
    providers — so diagnostics stay pipeline-owned.
    """

    def __init__(self) -> None:
        self._stages: list[StageTiming] = []

    @contextmanager
    def stage(self, stage: ExecutionStage) -> Iterator[None]:
        started_at = datetime.now(UTC)
        started = perf_counter()
        try:
            yield
        finally:
            finished_at = datetime.now(UTC)
            duration = perf_counter() - started
            self._stages.append(
                StageTiming(
                    stage=stage,
                    started_at=started_at,
                    finished_at=finished_at,
                    duration=duration,
                ),
            )

    def build(self, metrics: ExecutionMetrics) -> ExecutionTrace:
        return ExecutionTrace(stages=tuple(self._stages), metrics=metrics)
