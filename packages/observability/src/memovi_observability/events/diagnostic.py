"""Lightweight diagnostic events: log + metrics only, no event bus."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from memovi_observability.logging.structured import get_logger, log_operation
from memovi_observability.metrics import get_metrics_recorder


class DiagnosticEventName(StrEnum):
    DOCUMENT_UPLOADED = "DocumentUploaded"
    DOCUMENT_INDEXED = "DocumentIndexed"
    MEMORY_CREATED = "MemoryCreated"
    CONVERSATION_CREATED = "ConversationCreated"
    SEARCH_EXECUTED = "SearchExecuted"
    WORKSPACE_CREATED = "WorkspaceCreated"


# Mapping from pipeline domain event class names to diagnostic names.
DOMAIN_TO_DIAGNOSTIC: dict[str, DiagnosticEventName] = {
    "DocumentCreated": DiagnosticEventName.DOCUMENT_UPLOADED,
    "SearchIndexed": DiagnosticEventName.DOCUMENT_INDEXED,
    "KnowledgeMaterialized": DiagnosticEventName.MEMORY_CREATED,
}


class DiagnosticEventEmitter:
    """Emit standardized diagnostic events as structured logs and counters."""

    def __init__(self, *, logger_name: str = "memovi.diagnostics") -> None:
        self._logger = get_logger(logger_name)

    def emit(
        self,
        event: DiagnosticEventName | str,
        *,
        status: str = "emitted",
        **fields: Any,
    ) -> None:
        event_name = event.value if isinstance(event, DiagnosticEventName) else str(event)
        metrics = get_metrics_recorder()
        metrics.increment(
            "memovi.diagnostic_events",
            tags={"event": event_name, "status": status},
        )
        log_operation(
            self._logger,
            operation=f"diagnostic.{event_name}",
            status=status,
            event=event_name,
            **fields,
        )

    def emit_for_domain_event(
        self,
        domain_event: object,
        *,
        extra: dict[str, Any] | None = None,
    ) -> DiagnosticEventName | None:
        """Bridge a pipeline domain event into a diagnostic log when mapped."""
        diagnostic = DOMAIN_TO_DIAGNOSTIC.get(type(domain_event).__name__)
        if diagnostic is None:
            return None

        payload = dict(extra or {})
        for attr in (
            "document_id",
            "knowledge_item_id",
            "search_document_id",
            "document_version_id",
            "workspace_id",
            "chunk_count",
            "processing_job_id",
        ):
            if hasattr(domain_event, attr):
                value = getattr(domain_event, attr)
                payload[attr] = str(value) if value is not None else None

        if "document_id" not in payload and hasattr(domain_event, "document_id"):
            doc_id = getattr(domain_event, "document_id")
            payload["document_id"] = getattr(doc_id, "value", str(doc_id))

        self.emit(diagnostic, **payload)
        return diagnostic
