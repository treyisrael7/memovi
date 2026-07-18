"""Future-compatible metrics recording without requiring a Prometheus exporter."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Protocol


class MetricsRecorder(Protocol):
    def increment(
        self,
        name: str,
        *,
        value: float = 1.0,
        tags: dict[str, str] | None = None,
    ) -> None: ...

    def timing(
        self,
        name: str,
        duration_ms: float,
        *,
        tags: dict[str, str] | None = None,
    ) -> None: ...

    def histogram(
        self,
        name: str,
        value: float,
        *,
        tags: dict[str, str] | None = None,
    ) -> None: ...


@dataclass
class InMemoryMetricsRecorder:
    """In-process metrics sink suitable for tests and local development."""

    counters: dict[str, float] = field(default_factory=lambda: defaultdict(float))
    timings: dict[str, list[float]] = field(default_factory=lambda: defaultdict(list))
    histograms: dict[str, list[float]] = field(default_factory=lambda: defaultdict(list))
    tagged_counters: list[tuple[str, float, dict[str, str]]] = field(default_factory=list)
    tagged_timings: list[tuple[str, float, dict[str, str]]] = field(default_factory=list)

    def increment(
        self,
        name: str,
        *,
        value: float = 1.0,
        tags: dict[str, str] | None = None,
    ) -> None:
        self.counters[name] += value
        self.tagged_counters.append((name, value, dict(tags or {})))

    def timing(
        self,
        name: str,
        duration_ms: float,
        *,
        tags: dict[str, str] | None = None,
    ) -> None:
        self.timings[name].append(duration_ms)
        self.tagged_timings.append((name, duration_ms, dict(tags or {})))
        self.histogram(name, duration_ms, tags=tags)

    def histogram(
        self,
        name: str,
        value: float,
        *,
        tags: dict[str, str] | None = None,
    ) -> None:
        self.histograms[name].append(value)
        _ = tags

    def reset(self) -> None:
        self.counters.clear()
        self.timings.clear()
        self.histograms.clear()
        self.tagged_counters.clear()
        self.tagged_timings.clear()


_metrics_recorder: MetricsRecorder = InMemoryMetricsRecorder()


def get_metrics_recorder() -> MetricsRecorder:
    return _metrics_recorder


def set_metrics_recorder(recorder: MetricsRecorder) -> None:
    global _metrics_recorder
    _metrics_recorder = recorder
