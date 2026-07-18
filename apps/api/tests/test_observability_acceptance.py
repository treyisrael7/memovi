"""Acceptance verification for Milestone 14 observability criteria."""

from __future__ import annotations

import json
import logging
import time
from collections.abc import Iterator
from datetime import UTC, datetime
from typing import Annotated
from unittest.mock import patch
from uuid import uuid4

import pytest
from api.database import database_session as api_database_session
from api.events import InProcessEventDispatcher
from api.health import _check_database, run_readiness_checks
from api.middleware import REQUEST_ID_HEADER, register_middleware
from api.observability_bridge import register_observability_event_bridge
from api.workspace_context import (
    WORKSPACE_HEADER,
    BoundRequestContext,
    get_active_workspace_id,
    get_request_context_dependency,
)
from documents.domain.events import DocumentCreated
from documents.domain.value_objects import DocumentId
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from memovi_observability import (
    DiagnosticEventName,
    InMemoryMetricsRecorder,
    JsonFormatter,
    RequestContext,
    bind_request_context,
    clear_request_context,
    configure_structured_logging,
    get_logger,
    set_metrics_recorder,
    timed_operation,
)
from memovi_observability.logging.structured import RequestContextFilter, log_operation
from memovi_shared import DEFAULT_WORKSPACE_ID, WorkspaceId
from memovi_workspace.infrastructure.persistence import Base as WorkspaceBase
from memovi_workspace.infrastructure.persistence.models import WorkspaceRecord
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool


@pytest.fixture
def metrics_recorder() -> Iterator[InMemoryMetricsRecorder]:
    recorder = InMemoryMetricsRecorder()
    set_metrics_recorder(recorder)
    yield recorder
    set_metrics_recorder(InMemoryMetricsRecorder())


@pytest.fixture(autouse=True)
def _stamp_request_context_on_logs() -> Iterator[None]:
    """Ensure caplog records receive request-context fields during acceptance tests."""
    configure_structured_logging()
    root = logging.getLogger()
    context_filter = RequestContextFilter()
    root.addFilter(context_filter)
    yield
    root.removeFilter(context_filter)


class _WorkspaceFixture:
    def __init__(
        self,
        *,
        app: FastAPI,
        engine: Engine,
        workspace_a: WorkspaceId,
        workspace_b: WorkspaceId,
    ) -> None:
        self.app = app
        self.engine = engine
        self.workspace_a = workspace_a
        self.workspace_b = workspace_b

    def dispose(self) -> None:
        self.engine.dispose()


def _workspace_app() -> _WorkspaceFixture:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    WorkspaceBase.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    workspace_a = WorkspaceId.new()
    workspace_b = WorkspaceId.new()

    with Session(engine) as session:
        session.add(
            WorkspaceRecord(
                id=DEFAULT_WORKSPACE_ID.value,
                name="Default",
                created_at=datetime(2026, 1, 1, tzinfo=UTC),
            )
        )
        session.add(
            WorkspaceRecord(
                id=workspace_a.value,
                name="Alpha",
                created_at=datetime(2026, 1, 2, tzinfo=UTC),
            )
        )
        session.add(
            WorkspaceRecord(
                id=workspace_b.value,
                name="Beta",
                created_at=datetime(2026, 1, 3, tzinfo=UTC),
            )
        )
        session.commit()

    def database_session() -> Iterator[Session]:
        session = session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    app = FastAPI()
    register_middleware(app)
    app.dependency_overrides[api_database_session] = database_session

    @app.get("/probe")
    def probe(
        workspace_id: Annotated[WorkspaceId, Depends(get_active_workspace_id)],
        context: Annotated[BoundRequestContext, Depends(get_request_context_dependency)],
    ) -> dict[str, str]:
        with timed_operation("search.execute", attributes={"layer": "search"}):
            log_operation(
                get_logger("memovi.search"),
                operation="search.execute",
                status="success",
            )
        with timed_operation("memory.lookup", attributes={"layer": "memory"}):
            log_operation(
                get_logger("memovi.memory"),
                operation="memory.lookup",
                status="success",
            )
        with timed_operation("conversation.create", attributes={"layer": "intelligence"}):
            log_operation(
                get_logger("memovi.intelligence"),
                operation="conversation.create",
                status="success",
            )
        return {
            "request_id": context.request_id,
            "workspace_id": workspace_id.value,
        }

    return _WorkspaceFixture(
        app=app,
        engine=engine,
        workspace_a=workspace_a,
        workspace_b=workspace_b,
    )


def test_request_id_constant_across_search_memory_intelligence_logs(
    caplog: pytest.LogCaptureFixture,
) -> None:
    fixture = _workspace_app()
    try:
        with caplog.at_level(logging.INFO):
            with TestClient(fixture.app) as client:
                response = client.get(
                    "/probe",
                    headers={
                        REQUEST_ID_HEADER: "req-cross-domain-1",
                        WORKSPACE_HEADER: fixture.workspace_a.value,
                    },
                )

        assert response.status_code == 200
        assert response.json()["request_id"] == "req-cross-domain-1"
        assert response.headers[REQUEST_ID_HEADER] == "req-cross-domain-1"

        domain_ops = {"search.execute", "memory.lookup", "conversation.create", "http.request"}
        request_ids = {
            getattr(record, "request_id")
            for record in caplog.records
            if getattr(record, "operation", None) in domain_ops
        }
        assert request_ids == {"req-cross-domain-1"}
    finally:
        fixture.dispose()


def test_workspace_switch_changes_logged_workspace_id(
    caplog: pytest.LogCaptureFixture,
) -> None:
    fixture = _workspace_app()
    try:
        with caplog.at_level(logging.INFO):
            with TestClient(fixture.app) as client:
                first = client.get(
                    "/probe",
                    headers={
                        REQUEST_ID_HEADER: "req-ws-a",
                        WORKSPACE_HEADER: fixture.workspace_a.value,
                    },
                )
                second = client.get(
                    "/probe",
                    headers={
                        REQUEST_ID_HEADER: "req-ws-b",
                        WORKSPACE_HEADER: fixture.workspace_b.value,
                    },
                )

        assert first.status_code == 200
        assert second.status_code == 200
        assert first.json()["workspace_id"] == fixture.workspace_a.value
        assert second.json()["workspace_id"] == fixture.workspace_b.value
        assert first.json()["workspace_id"] != second.json()["workspace_id"]

        workspace_by_request = {
            getattr(record, "request_id"): getattr(record, "workspace_id")
            for record in caplog.records
            if getattr(record, "operation", None) == "http.request"
            and hasattr(record, "request_id")
            and hasattr(record, "workspace_id")
        }
        assert workspace_by_request.get("req-ws-a") == fixture.workspace_a.value
        assert workspace_by_request.get("req-ws-b") == fixture.workspace_b.value
    finally:
        fixture.dispose()


def test_structured_logs_are_valid_json_with_consistent_fields() -> None:
    token = bind_request_context(
        RequestContext.create(
            request_id="req-json-1",
            workspace_id=DEFAULT_WORKSPACE_ID,
            correlation_id="corr-json-1",
        )
    )
    try:
        record = logging.LogRecord(
            name="memovi.test",
            level=logging.INFO,
            pathname=__file__,
            lineno=1,
            msg="structured",
            args=(),
            exc_info=None,
        )
        record.operation = "search.execute"
        record.status = "success"
        record.duration_ms = 12.5
        record.repository = "SqlAlchemySearchRepository"
        record.event = "SearchExecuted"
        RequestContextFilter().filter(record)
        payload = json.loads(JsonFormatter().format(record))
    finally:
        clear_request_context(token)

    assert payload["request_id"] == "req-json-1"
    assert payload["workspace_id"] == DEFAULT_WORKSPACE_ID.value
    assert payload["correlation_id"] == "corr-json-1"
    assert payload["operation"] == "search.execute"
    assert payload["status"] == "success"
    assert payload["duration_ms"] == 12.5
    assert payload["repository"] == "SqlAlchemySearchRepository"
    assert payload["event"] == "SearchExecuted"
    assert payload["level"] == "INFO"
    assert "timestamp" in payload
    assert "message" in payload


def test_health_liveness_and_ready_healthy_shape() -> None:
    from api.health import router as health_router

    app = FastAPI()
    app.include_router(health_router)
    with TestClient(app) as client:
        health = client.get("/health")
        ready = client.get("/ready")

    assert health.status_code == 200
    assert health.json() == {"status": "healthy"}
    assert ready.status_code in {200, 503}
    body = ready.json()
    assert set(body.keys()) >= {"status", "components"}
    assert {c["name"] for c in body["components"]} == {
        "database",
        "vector_search",
        "embedding_provider",
        "migrations",
        "workspace",
        "search_readiness",
    }


def test_ready_reports_database_down_when_engine_unavailable() -> None:
    class BrokenEngine:
        def connect(self) -> object:
            raise ConnectionError("postgres is stopped")

    with patch("api.health.engine", return_value=BrokenEngine()):
        check = _check_database()
        assert check.status == "down"
        assert check.detail is not None
        assert "postgres is stopped" in check.detail

        checks = run_readiness_checks()
        by_name = {item.name: item for item in checks}
        assert by_name["database"].status == "down"
        assert any(item.status == "down" for item in checks)


def test_event_bridge_emits_single_document_uploaded_diagnostic(
    metrics_recorder: InMemoryMetricsRecorder,
    caplog: pytest.LogCaptureFixture,
) -> None:
    dispatcher = InProcessEventDispatcher()
    register_observability_event_bridge(dispatcher)
    register_observability_event_bridge(dispatcher)  # idempotent — no duplicates

    event = DocumentCreated(document_id=DocumentId(str(uuid4())), occurred_at=datetime.now(UTC))
    with caplog.at_level(logging.INFO, logger="memovi.diagnostics"):
        dispatcher.publish(event)

    uploaded = [
        record
        for record in caplog.records
        if getattr(record, "event", None) == DiagnosticEventName.DOCUMENT_UPLOADED
    ]
    assert len(uploaded) == 1
    assert metrics_recorder.counters["memovi.documents.upload"] == 1.0
    assert len(dispatcher.published_events) == 1
    assert isinstance(dispatcher.published_events[0], DocumentCreated)


def test_timed_operation_overhead_is_small() -> None:
    set_metrics_recorder(InMemoryMetricsRecorder())
    iterations = 2000

    started = time.perf_counter()
    for _ in range(iterations):
        pass
    baseline_ms = (time.perf_counter() - started) * 1000.0

    started = time.perf_counter()
    for _ in range(iterations):
        with timed_operation("bench.noop"):
            pass
    instrumented_ms = (time.perf_counter() - started) * 1000.0

    per_op_ms = (instrumented_ms - baseline_ms) / iterations
    assert per_op_ms < 1.0
