"""Timed operation helper combining structured logs, metrics, and spans."""

from __future__ import annotations

import time
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from memovi_observability.logging.structured import get_logger, log_operation
from memovi_observability.metrics import get_metrics_recorder
from memovi_observability.tracing import start_span


@contextmanager
def timed_operation(
    operation: str,
    *,
    repository: str | None = None,
    logger_name: str = "memovi.timing",
    metric_name: str | None = None,
    attributes: dict[str, Any] | None = None,
) -> Iterator[None]:
    """Measure an operation, emit structured log + metric, and wrap in a span."""
    logger = get_logger(logger_name)
    metrics = get_metrics_recorder()
    metric = metric_name or f"memovi.operation.{operation}"
    tags: dict[str, str] = {"operation": operation}
    if repository is not None:
        tags["repository"] = repository

    span_attrs = dict(attributes or {})
    span_attrs["operation"] = operation
    if repository is not None:
        span_attrs["repository"] = repository

    started = time.perf_counter()
    status = "success"
    error: str | None = None
    with start_span(operation, attributes=span_attrs):
        try:
            yield
        except Exception as exc:
            status = "error"
            error = str(exc)
            raise
        finally:
            duration_ms = (time.perf_counter() - started) * 1000.0
            metrics.timing(metric, duration_ms, tags=tags)
            metrics.increment(
                f"{metric}.count",
                tags={**tags, "status": status},
            )
            log_operation(
                logger,
                operation=operation,
                status=status,
                duration_ms=duration_ms,
                repository=repository,
                error=error,
            )
