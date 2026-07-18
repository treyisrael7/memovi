"""Structured JSON logging with request-context field injection."""

from __future__ import annotations

import json
import logging
import sys
from datetime import UTC, datetime
from typing import Any

from memovi_observability.request_context import get_request_context

STANDARD_RECORD_ATTRS = {
    "name",
    "msg",
    "args",
    "levelname",
    "levelno",
    "pathname",
    "filename",
    "module",
    "exc_info",
    "exc_text",
    "stack_info",
    "lineno",
    "funcName",
    "created",
    "msecs",
    "relativeCreated",
    "thread",
    "threadName",
    "processName",
    "process",
    "taskName",
    "message",
    "asctime",
}


class RequestContextFilter(logging.Filter):
    """Stamp bound RequestContext fields onto each LogRecord at emit time."""

    def filter(self, record: logging.LogRecord) -> bool:
        context = get_request_context()
        if context is None:
            return True
        for key, value in context.as_log_fields().items():
            if not hasattr(record, key):
                setattr(record, key, value)
        return True


class JsonFormatter(logging.Formatter):
    """Format log records as single-line JSON with consistent field names."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Prefer fields stamped on the record (emit-time); fall back to ambient context.
        context = get_request_context()
        if context is not None:
            payload.update(context.as_log_fields())

        for key, value in record.__dict__.items():
            if key in STANDARD_RECORD_ATTRS or key.startswith("_"):
                continue
            payload[key] = value

        if record.exc_info:
            payload["error"] = self.formatException(record.exc_info)

        return json.dumps(payload, default=str, separators=(",", ":"))


def configure_structured_logging(*, level: int = logging.INFO) -> None:
    """Configure root logging for structured JSON output."""
    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(level)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    handler.addFilter(RequestContextFilter())
    root.addHandler(handler)

    # Also attach to the root logger so caplog / non-handler paths see stamped fields.
    context_filter = RequestContextFilter()
    if not any(isinstance(existing, RequestContextFilter) for existing in root.filters):
        root.addFilter(context_filter)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def log_operation(
    logger: logging.Logger,
    *,
    operation: str,
    status: str,
    duration_ms: float | None = None,
    repository: str | None = None,
    error: str | None = None,
    level: int = logging.INFO,
    **extra: Any,
) -> None:
    """Emit a structured operation log with consistent field names."""
    fields: dict[str, Any] = {
        "operation": operation,
        "status": status,
        **extra,
    }
    context = get_request_context()
    if context is not None:
        fields.update(context.as_log_fields())
    if duration_ms is not None:
        fields["duration_ms"] = round(duration_ms, 3)
    if repository is not None:
        fields["repository"] = repository
    if error is not None:
        fields["error"] = error

    logger.log(level, operation, extra=fields)
