"""Integration coverage for Knowledge Explorer Memory and Documents read APIs."""

from __future__ import annotations

import time
from collections.abc import Iterator

import pytest
from api.app import create_app
from api.document_processing import configure_document_processing
from api.documents_session import build_documents_database_session
from auth.api.dependencies import get_database_session as get_auth_database_session
from auth.infrastructure.persistence import Base as AuthBase
from documents.api.dependencies import get_database_session as get_documents_database_session
from documents.api.dependencies import get_object_storage
from documents.application.workers import DocumentProcessingWorkerConfig
from documents.domain.enums import ProcessingStatus
from documents.infrastructure.persistence import Base as DocumentsBase
from documents.infrastructure.persistence.models import ProcessingJobRecord
from documents.infrastructure.queue import InMemoryProcessingJobQueue
from fastapi.testclient import TestClient
from memovi_memory.api.dependencies import get_database_session as get_memory_database_session
from memovi_memory.infrastructure.persistence.models import Base as MemoryBase
from memovi_memory.infrastructure.persistence.models import KnowledgeItemRecord
from memovi_search.api.dependencies import get_database_session as get_search_database_session
from memovi_search.infrastructure.persistence.models import Base as SearchBase
from memovi_shared import DEFAULT_WORKSPACE_ID
from memovi_workspace.api.dependencies import get_database_session as get_workspace_database_session
from memovi_workspace.infrastructure.persistence import Base as WorkspaceBase
from memovi_workspace.infrastructure.persistence.models import WorkspaceRecord
from postgres_support import ensure_pgvector_extension, postgres_available, postgres_database_url
from sqlalchemy import Engine, create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from datetime import UTC, datetime

WORKSPACE_HEADER = "X-Memovi-Workspace-Id"


class InMemoryObjectStorage:
    def __init__(self) -> None:
        self.objects: dict[str, tuple[bytes, str]] = {}

    def put_object(self, *, key: str, content: bytes, content_type: str) -> None:
        self.objects[key] = (content, content_type)

    def get_object(self, key: str) -> bytes:
        return self.objects[key][0]


def _seed_default_workspace(engine: Engine) -> None:
    with Session(engine) as session:
        existing = session.get(WorkspaceRecord, DEFAULT_WORKSPACE_ID.value)
        if existing is None:
            session.add(
                WorkspaceRecord(
                    id=DEFAULT_WORKSPACE_ID.value,
                    name="Default",
                    created_at=datetime(2026, 1, 1, tzinfo=UTC),
                )
            )
            session.commit()


def _wait_for_job_status(
    engine: Engine,
    processing_job_id: str,
    expected_status: ProcessingStatus,
    *,
    timeout_seconds: float = 10.0,
) -> ProcessingJobRecord:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        with Session(engine) as session:
            job = session.get(ProcessingJobRecord, processing_job_id)
            if job is not None and job.status == expected_status.value:
                return job
        time.sleep(0.05)
    with Session(engine) as session:
        job = session.get(ProcessingJobRecord, processing_job_id)
        current_status = job.status if job is not None else "missing"
    pytest.fail(
        f"Processing job {processing_job_id} did not reach {expected_status.value} "
        f"within {timeout_seconds}s (last status: {current_status})."
    )


def _wait_for_knowledge(
    engine: Engine,
    *,
    minimum_count: int = 1,
    timeout_seconds: float = 10.0,
) -> list[KnowledgeItemRecord]:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        with Session(engine) as session:
            items = list(session.scalars(select(KnowledgeItemRecord)).all())
            if len(items) >= minimum_count:
                return items
        time.sleep(0.05)
    with Session(engine) as session:
        count = len(list(session.scalars(select(KnowledgeItemRecord)).all()))
    pytest.fail(
        f"Expected at least {minimum_count} knowledge items within "
        f"{timeout_seconds}s (found {count})."
    )


@pytest.fixture
def explorer_client() -> Iterator[tuple[TestClient, Engine]]:
    if not postgres_available():
        pytest.skip("PostgreSQL is required for knowledge explorer integration tests.")

    object_storage = InMemoryObjectStorage()
    engine = create_engine(postgres_database_url(), pool_pre_ping=True)
    ensure_pgvector_extension(engine)

    for base in (
        AuthBase,
        WorkspaceBase,
        DocumentsBase,
        MemoryBase,
        SearchBase,
    ):
        base.metadata.drop_all(engine)
    for base in (
        AuthBase,
        WorkspaceBase,
        DocumentsBase,
        MemoryBase,
        SearchBase,
    ):
        base.metadata.create_all(engine)

    _seed_default_workspace(engine)
    test_session_factory = sessionmaker(bind=engine, expire_on_commit=False)

    def database_session() -> Iterator[Session]:
        session = test_session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def worker_session_factory() -> Session:
        return test_session_factory()

    app = create_app()
    queue = InMemoryProcessingJobQueue()
    configure_document_processing(
        app,
        session_factory=worker_session_factory,
        queue=queue,
        worker_config=DocumentProcessingWorkerConfig(
            max_retries=3,
            poll_interval_seconds=0.05,
        ),
        object_storage=object_storage,
    )
    app.dependency_overrides[get_auth_database_session] = database_session
    app.dependency_overrides[get_documents_database_session] = build_documents_database_session(
        database_session
    )
    app.dependency_overrides[get_memory_database_session] = database_session
    app.dependency_overrides[get_search_database_session] = database_session
    app.dependency_overrides[get_workspace_database_session] = database_session
    app.dependency_overrides[get_object_storage] = lambda: object_storage

    with TestClient(app, base_url="https://testserver") as client:
        yield (client, engine)
    engine.dispose()


def test_knowledge_explorer_apis_after_ingest(
    explorer_client: tuple[TestClient, Engine],
) -> None:
    client, engine = explorer_client
    headers = {WORKSPACE_HEADER: DEFAULT_WORKSPACE_ID.value}

    upload = client.post(
        "/documents",
        headers=headers,
        files={
            "file": (
                "explorer-note.md",
                b"# Explorer\n\nMemovi knowledge should be inspectable.",
                "text/markdown",
            )
        },
    )
    assert upload.status_code == 202
    document_id = upload.json()["document_id"]
    _wait_for_job_status(engine, upload.json()["processing_job_id"], ProcessingStatus.COMPLETED)
    knowledge_rows = _wait_for_knowledge(engine)
    knowledge_id = knowledge_rows[0].id

    documents = client.get("/documents", headers=headers)
    assert documents.status_code == 200
    assert any(item["id"] == document_id for item in documents.json()["items"])

    document = client.get(f"/documents/{document_id}", headers=headers)
    assert document.status_code == 200
    assert document.json()["name"] == "explorer-note.md"

    dashboard = client.get("/memory/dashboard", headers=headers)
    assert dashboard.status_code == 200
    body = dashboard.json()
    assert body["knowledge_item_count"] >= 1
    assert body["source_document_count"] >= 1

    entities = client.get("/memory", headers=headers)
    assert entities.status_code == 200
    assert entities.json()["count"] >= 1
    assert any(item["id"] == knowledge_id for item in entities.json()["items"])

    filtered = client.get(
        "/memory",
        headers=headers,
        params={"document_id": document_id, "entity_type": "upload"},
    )
    assert filtered.status_code == 200
    assert filtered.json()["count"] >= 1

    detail = client.get(f"/memory/{knowledge_id}", headers=headers)
    assert detail.status_code == 200
    detail_body = detail.json()
    assert detail_body["document_id"] == document_id
    assert detail_body["confidence"] is None
    assert len(detail_body["chunks"]) >= 1

    concepts = client.get("/memory/concepts", headers=headers)
    assert concepts.status_code == 200
    assert concepts.json()["count"] >= 1

    relationships = client.get("/memory/relationships", headers=headers)
    assert relationships.status_code == 200
    rel_types = {item["relationship_type"] for item in relationships.json()["items"]}
    assert "document_of" in rel_types
    assert "chunk_of" in rel_types

    search = client.get("/search", headers=headers, params={"q": "inspectable", "mode": "keyword"})
    assert search.status_code == 200
    assert search.json()["count"] >= 1
