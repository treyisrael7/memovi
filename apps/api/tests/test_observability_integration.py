"""Integration coverage for request context, diagnostic bridge, and health."""

from __future__ import annotations

import logging
from collections.abc import Iterator
from datetime import UTC, datetime
from typing import Annotated
from uuid import uuid4

import pytest
from api.database import database_session as api_database_session
from api.events import InProcessEventDispatcher
from api.health import _check_embedding_provider
from api.middleware import CORRELATION_ID_HEADER, REQUEST_ID_HEADER
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
from memovi_memory.domain.events import KnowledgeMaterialized
from memovi_observability import (
    DiagnosticEventName,
    InMemoryMetricsRecorder,
    RequestContext,
    bind_request_context,
    clear_request_context,
    get_request_context,
    set_metrics_recorder,
)
from memovi_search.domain.events import SearchIndexed
from memovi_shared import DEFAULT_WORKSPACE_ID, WorkspaceId
from memovi_workspace.infrastructure.persistence import Base as WorkspaceBase
from memovi_workspace.infrastructure.persistence.models import WorkspaceRecord
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool


@pytest.fixture
def metrics_recorder() -> Iterator[InMemoryMetricsRecorder]:
    recorder = InMemoryMetricsRecorder()
    set_metrics_recorder(recorder)
    yield recorder
    set_metrics_recorder(InMemoryMetricsRecorder())


def test_request_id_is_echoed_and_stable_across_handler() -> None:
    app = FastAPI()
    from api.middleware import register_middleware

    register_middleware(app)

    @app.get("/probe")
    def probe(
        context: Annotated[BoundRequestContext, Depends(get_request_context_dependency)],
    ) -> dict[str, str | None]:
        return {
            "request_id": context.request_id,
            "correlation_id": context.correlation_id,
            "bound_request_id": (
                get_request_context().request_id if get_request_context() else None
            ),
        }

    with TestClient(app) as client:
        response = client.get(
            "/probe",
            headers={
                REQUEST_ID_HEADER: "req-stable-1",
                CORRELATION_ID_HEADER: "corr-1",
            },
        )

    assert response.status_code == 200
    assert response.headers[REQUEST_ID_HEADER] == "req-stable-1"
    assert response.headers[CORRELATION_ID_HEADER] == "corr-1"
    body = response.json()
    assert body["request_id"] == "req-stable-1"
    assert body["bound_request_id"] == "req-stable-1"
    assert body["correlation_id"] == "corr-1"


def test_workspace_id_bound_into_request_context() -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    WorkspaceBase.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    explicit = WorkspaceId.new()

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
                id=explicit.value,
                name="Explicit",
                created_at=datetime(2026, 1, 2, tzinfo=UTC),
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
    from api.middleware import register_middleware

    register_middleware(app)
    app.dependency_overrides[api_database_session] = database_session

    @app.get("/active-workspace")
    def active_workspace(
        workspace_id: Annotated[WorkspaceId, Depends(get_active_workspace_id)],
        context: Annotated[BoundRequestContext, Depends(get_request_context_dependency)],
    ) -> dict[str, str | None]:
        return {
            "workspace_id": workspace_id.value,
            "context_workspace_id": (
                context.workspace_id.value if context.workspace_id is not None else None
            ),
            "request_id": context.request_id,
        }

    try:
        with TestClient(app) as client:
            response = client.get(
                "/active-workspace",
                headers={
                    REQUEST_ID_HEADER: "req-ws-1",
                    WORKSPACE_HEADER: explicit.value,
                },
            )

        assert response.status_code == 200
        body = response.json()
        assert body["workspace_id"] == explicit.value
        assert body["context_workspace_id"] == explicit.value
        assert body["request_id"] == "req-ws-1"
    finally:
        engine.dispose()


def test_observability_bridge_emits_diagnostic_events(
    metrics_recorder: InMemoryMetricsRecorder,
    caplog: pytest.LogCaptureFixture,
) -> None:
    dispatcher = InProcessEventDispatcher()
    register_observability_event_bridge(dispatcher)
    now = datetime.now(UTC)
    token = bind_request_context(
        RequestContext.create(
            request_id="req-bridge-1",
            workspace_id=DEFAULT_WORKSPACE_ID,
        )
    )
    try:
        with caplog.at_level(logging.INFO, logger="memovi.diagnostics"):
            dispatcher.publish(
                DocumentCreated(
                    document_id=DocumentId(str(uuid4())),
                    occurred_at=now,
                )
            )
            dispatcher.publish(
                KnowledgeMaterialized(
                    knowledge_item_id=str(uuid4()),
                    workspace_id=DEFAULT_WORKSPACE_ID.value,
                    document_id=str(uuid4()),
                    document_version_id=str(uuid4()),
                    chunk_count=1,
                    occurred_at=now,
                )
            )
            dispatcher.publish(
                SearchIndexed(
                    search_document_id=str(uuid4()),
                    knowledge_item_id=str(uuid4()),
                    document_id=str(uuid4()),
                    document_version_id=str(uuid4()),
                    indexed_at=now,
                )
            )
    finally:
        clear_request_context(token)

    events = {
        getattr(record, "event", None)
        for record in caplog.records
        if getattr(record, "event", None) is not None
    }
    assert DiagnosticEventName.DOCUMENT_UPLOADED in events
    assert DiagnosticEventName.MEMORY_CREATED in events
    assert DiagnosticEventName.DOCUMENT_INDEXED in events
    assert metrics_recorder.counters["memovi.documents.upload"] == 1.0
    assert metrics_recorder.counters["memovi.memory.created"] == 1.0
    assert metrics_recorder.counters["memovi.documents.indexed"] == 1.0


def test_health_liveness_endpoint() -> None:
    from api.health import router as health_router

    app = FastAPI()
    app.include_router(health_router)
    with TestClient(app) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_ready_endpoint_reports_components() -> None:
    from api.health import router as health_router

    app = FastAPI()
    app.include_router(health_router)
    with TestClient(app) as client:
        response = client.get("/ready")

    assert response.status_code in {200, 503}
    payload = response.json()
    assert payload["status"] in {"ready", "not_ready"}
    names = {component["name"] for component in payload["components"]}
    assert names == {
        "database",
        "vector_search",
        "embedding_provider",
        "migrations",
        "workspace",
        "search_readiness",
    }


def test_embedding_provider_readiness_is_up() -> None:
    assert _check_embedding_provider().status == "up"
