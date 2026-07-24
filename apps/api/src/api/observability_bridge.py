"""Bridge pipeline domain events into diagnostic observability logs.

The in-process event bus remains the source of truth for domain facts.
This adapter only maps known domain events to standardized diagnostic names.
"""

from __future__ import annotations

from documents.domain.events import DocumentCreated
from memovi_memory.domain.events import KnowledgeMaterialized
from memovi_observability import DiagnosticEventEmitter, get_metrics_recorder
from memovi_search.domain.events import SearchIndexed

from api.events import InProcessEventDispatcher

_EMITTER = DiagnosticEventEmitter()


def register_observability_event_bridge(dispatcher: InProcessEventDispatcher) -> None:
    """Subscribe diagnostic logging to pipeline domain events.

    Idempotent: repeated registration on the same dispatcher is a no-op so
    diagnostic events are never duplicated.
    """
    if getattr(dispatcher, "_memovi_observability_bridge_registered", False):
        return

    def on_document_created(event: object) -> None:
        if not isinstance(event, DocumentCreated):
            return
        _EMITTER.emit_for_domain_event(event)
        get_metrics_recorder().increment("memovi.documents.upload")

    def on_knowledge_materialized(event: object) -> None:
        if not isinstance(event, KnowledgeMaterialized):
            return
        _EMITTER.emit_for_domain_event(event)
        get_metrics_recorder().increment("memovi.memory.created")

    def on_search_indexed(event: object) -> None:
        if not isinstance(event, SearchIndexed):
            return
        _EMITTER.emit_for_domain_event(event)
        get_metrics_recorder().increment("memovi.documents.indexed")

    dispatcher.subscribe(DocumentCreated, on_document_created)
    dispatcher.subscribe(KnowledgeMaterialized, on_knowledge_materialized)
    dispatcher.subscribe(SearchIndexed, on_search_indexed)
    dispatcher._memovi_observability_bridge_registered = True
