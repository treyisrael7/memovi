from dataclasses import dataclass
from datetime import UTC, datetime

from memovi_observability import (
    DiagnosticEventEmitter,
    DiagnosticEventName,
    InMemoryMetricsRecorder,
    set_metrics_recorder,
)
from memovi_observability.events import DOMAIN_TO_DIAGNOSTIC


@dataclass(frozen=True, slots=True)
class DocumentCreated:
    document_id: str
    occurred_at: datetime


@dataclass(frozen=True, slots=True)
class KnowledgeMaterialized:
    knowledge_item_id: str
    workspace_id: str
    document_id: str
    document_version_id: str
    chunk_count: int
    occurred_at: datetime


@dataclass(frozen=True, slots=True)
class SearchIndexed:
    search_document_id: str
    knowledge_item_id: str
    document_id: str
    document_version_id: str
    indexed_at: datetime


def test_domain_to_diagnostic_mapping() -> None:
    assert DOMAIN_TO_DIAGNOSTIC["DocumentCreated"] == DiagnosticEventName.DOCUMENT_UPLOADED
    assert DOMAIN_TO_DIAGNOSTIC["SearchIndexed"] == DiagnosticEventName.DOCUMENT_INDEXED
    assert DOMAIN_TO_DIAGNOSTIC["KnowledgeMaterialized"] == DiagnosticEventName.MEMORY_CREATED


def test_emit_records_metric_and_event_name() -> None:
    recorder = InMemoryMetricsRecorder()
    set_metrics_recorder(recorder)
    emitter = DiagnosticEventEmitter()

    emitter.emit(DiagnosticEventName.WORKSPACE_CREATED, workspace_id="ws-1")

    assert recorder.counters["memovi.diagnostic_events"] == 1.0
    assert recorder.tagged_counters[0][2]["event"] == "WorkspaceCreated"


def test_emit_for_domain_event_bridges_pipeline_events() -> None:
    recorder = InMemoryMetricsRecorder()
    set_metrics_recorder(recorder)
    emitter = DiagnosticEventEmitter()
    now = datetime.now(UTC)

    assert (
        emitter.emit_for_domain_event(
            DocumentCreated(document_id="doc-1", occurred_at=now),
        )
        == DiagnosticEventName.DOCUMENT_UPLOADED
    )
    assert (
        emitter.emit_for_domain_event(
            KnowledgeMaterialized(
                knowledge_item_id="k-1",
                workspace_id="ws-1",
                document_id="doc-1",
                document_version_id="v-1",
                chunk_count=2,
                occurred_at=now,
            ),
        )
        == DiagnosticEventName.MEMORY_CREATED
    )
    assert (
        emitter.emit_for_domain_event(
            SearchIndexed(
                search_document_id="s-1",
                knowledge_item_id="k-1",
                document_id="doc-1",
                document_version_id="v-1",
                indexed_at=now,
            ),
        )
        == DiagnosticEventName.DOCUMENT_INDEXED
    )
    assert recorder.counters["memovi.diagnostic_events"] == 3.0
