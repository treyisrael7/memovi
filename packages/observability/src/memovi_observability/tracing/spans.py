"""Provider-neutral OpenTelemetry span helpers (API only; no exporter required)."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from opentelemetry import trace
from opentelemetry.trace import Span, Status, StatusCode, Tracer

from memovi_observability.request_context import get_request_context

TRACER_NAME = "memovi"


def get_tracer(name: str = TRACER_NAME) -> Tracer:
    return trace.get_tracer(name)


@contextmanager
def start_span(
    name: str,
    *,
    attributes: dict[str, Any] | None = None,
    tracer_name: str = TRACER_NAME,
) -> Iterator[Span]:
    """Start a child span, enriching attributes from the bound RequestContext."""
    tracer = get_tracer(tracer_name)
    attrs: dict[str, Any] = dict(attributes or {})
    context = get_request_context()
    if context is not None:
        attrs.setdefault("request_id", context.request_id)
        if context.workspace_id is not None:
            attrs.setdefault("workspace_id", context.workspace_id.value)
        if context.correlation_id is not None:
            attrs.setdefault("correlation_id", context.correlation_id)

    with tracer.start_as_current_span(name, attributes=attrs) as span:
        try:
            yield span
        except Exception as exc:
            span.record_exception(exc)
            span.set_status(Status(StatusCode.ERROR, str(exc)))
            raise
