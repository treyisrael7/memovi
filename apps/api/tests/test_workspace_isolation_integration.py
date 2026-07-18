"""Integration coverage for workspace ownership isolation."""

from __future__ import annotations

import time
from collections.abc import Iterator
from datetime import UTC, datetime

import pytest
from api.app import create_app
from api.database import database_session as api_database_session
from api.document_processing import configure_document_processing
from api.documents_session import build_documents_database_session
from api.search_integration import build_retrieve_knowledge
from auth.api.dependencies import get_database_session as get_auth_database_session
from auth.infrastructure.persistence import Base as AuthBase
from documents.api.dependencies import get_database_session as get_documents_database_session
from documents.api.dependencies import get_object_storage
from documents.application.workers import DocumentProcessingWorkerConfig
from documents.domain.enums import ProcessingStatus
from documents.infrastructure.persistence import Base as DocumentsBase
from documents.infrastructure.persistence.models import DocumentRecord, ProcessingJobRecord
from documents.infrastructure.queue import InMemoryProcessingJobQueue
from fastapi.testclient import TestClient
from memovi_intelligence.api.dependencies import (
    get_database_session as get_intelligence_database_session,
)
from memovi_intelligence.api.dependencies import get_knowledge_retriever
from memovi_intelligence.infrastructure import FakeKnowledgeRetriever
from memovi_intelligence.infrastructure.persistence import Base as IntelligenceBase
from memovi_memory.infrastructure.persistence.models import Base as MemoryBase
from memovi_memory.infrastructure.persistence.models import KnowledgeItemRecord
from memovi_search.api.dependencies import get_database_session as get_search_database_session
from memovi_search.application.queries import RetrieveKnowledgeQuery
from memovi_search.application.services import RetrievalMode
from memovi_search.infrastructure.persistence.models import Base as SearchBase
from memovi_search.infrastructure.persistence.models import SearchDocumentRecord
from memovi_shared import DEFAULT_WORKSPACE_ID, WorkspaceId
from memovi_workspace.api.dependencies import get_database_session as get_workspace_database_session
from memovi_workspace.infrastructure.persistence import Base as WorkspaceBase
from memovi_workspace.infrastructure.persistence.models import WorkspaceRecord
from postgres_support import ensure_pgvector_extension, postgres_available, postgres_database_url
from sqlalchemy import Engine, create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

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
    timeout_seconds: float = 15.0,
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
        f"Processing job {processing_job_id} did not reach "
        f"{expected_status.value} within {timeout_seconds}s (last status: {current_status}).",
    )


def _wait_for_search_documents(
    engine: Engine,
    *,
    workspace_id: str,
    minimum_count: int = 1,
    timeout_seconds: float = 15.0,
) -> list[SearchDocumentRecord]:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        with Session(engine) as session:
            documents = list(
                session.scalars(
                    select(SearchDocumentRecord).where(
                        SearchDocumentRecord.workspace_id == workspace_id,
                    )
                ).all()
            )
            if len(documents) >= minimum_count:
                return documents
        time.sleep(0.05)

    with Session(engine) as session:
        count = len(
            list(
                session.scalars(
                    select(SearchDocumentRecord).where(
                        SearchDocumentRecord.workspace_id == workspace_id,
                    )
                ).all()
            )
        )
    pytest.fail(
        f"Expected at least {minimum_count} search documents for workspace "
        f"{workspace_id} within {timeout_seconds}s (found {count}).",
    )


def _build_client(engine: Engine) -> Iterator[tuple[TestClient, Engine]]:
    _seed_default_workspace(engine)
    test_session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    object_storage = InMemoryObjectStorage()

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

    app = create_app()
    configure_document_processing(
        app,
        session_factory=test_session_factory,
        queue=InMemoryProcessingJobQueue(),
        worker_config=DocumentProcessingWorkerConfig(
            max_retries=3,
            poll_interval_seconds=0.05,
        ),
        object_storage=object_storage,
    )
    app.dependency_overrides[api_database_session] = database_session
    app.dependency_overrides[get_auth_database_session] = database_session
    app.dependency_overrides[get_documents_database_session] = build_documents_database_session(
        database_session
    )
    app.dependency_overrides[get_search_database_session] = database_session
    app.dependency_overrides[get_intelligence_database_session] = database_session
    app.dependency_overrides[get_workspace_database_session] = database_session
    app.dependency_overrides[get_object_storage] = lambda: object_storage
    app.dependency_overrides[get_knowledge_retriever] = lambda: FakeKnowledgeRetriever()

    with TestClient(app, base_url="https://testserver") as client:
        yield client, engine

    engine.dispose()


@pytest.fixture
def workspace_isolation_sqlite_client() -> Iterator[tuple[TestClient, Engine]]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    for base in (
        AuthBase,
        WorkspaceBase,
        DocumentsBase,
        MemoryBase,
        SearchBase,
        IntelligenceBase,
    ):
        base.metadata.create_all(engine)
    yield from _build_client(engine)


@pytest.fixture
def workspace_isolation_postgres_client() -> Iterator[tuple[TestClient, Engine]]:
    if not postgres_available():
        pytest.skip("PostgreSQL is required for workspace search isolation tests.")

    engine = create_engine(postgres_database_url(), pool_pre_ping=True)
    ensure_pgvector_extension(engine)
    # Drop owned tables before workspace so FK constraints from migrations do not block.
    for base in (
        IntelligenceBase,
        SearchBase,
        MemoryBase,
        DocumentsBase,
        AuthBase,
        WorkspaceBase,
    ):
        base.metadata.drop_all(engine)
    for base in (
        AuthBase,
        WorkspaceBase,
        DocumentsBase,
        MemoryBase,
        SearchBase,
        IntelligenceBase,
    ):
        base.metadata.create_all(engine)
    yield from _build_client(engine)


def _create_workspace(client: TestClient, name: str) -> str:
    response = client.post("/workspaces", json={"name": name})
    assert response.status_code == 201
    return response.json()["id"]


def _upload(
    client: TestClient,
    *,
    filename: str,
    content: bytes,
    workspace_id: str | None = None,
) -> dict[str, str]:
    headers = {WORKSPACE_HEADER: workspace_id} if workspace_id is not None else None
    response = client.post(
        "/documents",
        files={"file": (filename, content, "text/markdown")},
        headers=headers,
    )
    assert response.status_code == 202
    payload = response.json()
    return {
        "document_id": str(payload["document_id"]),
        "processing_job_id": str(payload["processing_job_id"]),
    }


def test_default_header_lands_in_default_workspace_and_stays_isolated(
    workspace_isolation_sqlite_client: tuple[TestClient, Engine],
) -> None:
    client, engine = workspace_isolation_sqlite_client
    other_workspace_id = _create_workspace(client, "Other")

    default_upload = _upload(
        client,
        filename="default.md",
        content=b"# Default workspace unique token alphaworkspace",
    )
    other_upload = _upload(
        client,
        filename="other.md",
        content=b"# Other workspace unique token betaworkspace",
        workspace_id=other_workspace_id,
    )

    _wait_for_job_status(engine, default_upload["processing_job_id"], ProcessingStatus.COMPLETED)
    _wait_for_job_status(engine, other_upload["processing_job_id"], ProcessingStatus.COMPLETED)
    _wait_for_search_documents(engine, workspace_id=DEFAULT_WORKSPACE_ID.value)
    _wait_for_search_documents(engine, workspace_id=other_workspace_id)

    with Session(engine) as session:
        default_doc = session.get(DocumentRecord, default_upload["document_id"])
        other_doc = session.get(DocumentRecord, other_upload["document_id"])
        assert default_doc is not None
        assert other_doc is not None
        assert default_doc.workspace_id == DEFAULT_WORKSPACE_ID.value
        assert other_doc.workspace_id == other_workspace_id

        default_knowledge = session.scalars(
            select(KnowledgeItemRecord).where(
                KnowledgeItemRecord.document_id == default_upload["document_id"],
            )
        ).all()
        other_knowledge = session.scalars(
            select(KnowledgeItemRecord).where(
                KnowledgeItemRecord.document_id == other_upload["document_id"],
            )
        ).all()
        assert len(default_knowledge) == 1
        assert len(other_knowledge) == 1
        assert default_knowledge[0].workspace_id == DEFAULT_WORKSPACE_ID.value
        assert other_knowledge[0].workspace_id == other_workspace_id

        default_search = session.scalars(
            select(SearchDocumentRecord).where(
                SearchDocumentRecord.workspace_id == DEFAULT_WORKSPACE_ID.value,
            )
        ).all()
        other_search = session.scalars(
            select(SearchDocumentRecord).where(
                SearchDocumentRecord.workspace_id == other_workspace_id,
            )
        ).all()
        assert len(default_search) == 1
        assert len(other_search) == 1
        assert default_search[0].document_id == default_upload["document_id"]
        assert other_search[0].document_id == other_upload["document_id"]

    default_conversation = client.post("/conversations")
    assert default_conversation.status_code == 201
    conversation_id = default_conversation.json()["conversation_id"]

    assert client.get(f"/conversations/{conversation_id}").status_code == 200
    assert (
        client.get(
            f"/conversations/{conversation_id}",
            headers={WORKSPACE_HEADER: other_workspace_id},
        ).status_code
        == 404
    )


def test_search_and_conversations_are_isolated_by_workspace(
    workspace_isolation_postgres_client: tuple[TestClient, Engine],
) -> None:
    client, engine = workspace_isolation_postgres_client
    workspace_a = _create_workspace(client, "Alpha")
    workspace_b = _create_workspace(client, "Beta")

    upload_a = _upload(
        client,
        filename="alpha.md",
        content=b"# Alpha\n\nUnique alphatokensecret appears only here.",
        workspace_id=workspace_a,
    )
    upload_b = _upload(
        client,
        filename="beta.md",
        content=b"# Beta\n\nUnique betatokensecret appears only here.",
        workspace_id=workspace_b,
    )

    _wait_for_job_status(engine, upload_a["processing_job_id"], ProcessingStatus.COMPLETED)
    _wait_for_job_status(engine, upload_b["processing_job_id"], ProcessingStatus.COMPLETED)
    _wait_for_search_documents(engine, workspace_id=workspace_a)
    _wait_for_search_documents(engine, workspace_id=workspace_b)

    with Session(engine) as session:
        search = build_retrieve_knowledge(session)
        alpha_results = search.execute(
            RetrieveKnowledgeQuery(
                query="alphatokensecret",
                mode=RetrievalMode.KEYWORD,
                limit=10,
                offset=0,
                workspace_id=WorkspaceId(workspace_a),
            )
        )
        beta_results = search.execute(
            RetrieveKnowledgeQuery(
                query="betatokensecret",
                mode=RetrievalMode.KEYWORD,
                limit=10,
                offset=0,
                workspace_id=WorkspaceId(workspace_b),
            )
        )
        alpha_cross = search.execute(
            RetrieveKnowledgeQuery(
                query="betatokensecret",
                mode=RetrievalMode.KEYWORD,
                limit=10,
                offset=0,
                workspace_id=WorkspaceId(workspace_a),
            )
        )
        beta_cross = search.execute(
            RetrieveKnowledgeQuery(
                query="alphatokensecret",
                mode=RetrievalMode.KEYWORD,
                limit=10,
                offset=0,
                workspace_id=WorkspaceId(workspace_b),
            )
        )

        assert len(alpha_results) == 1
        assert alpha_results[0].document_id == upload_a["document_id"]
        assert len(beta_results) == 1
        assert beta_results[0].document_id == upload_b["document_id"]
        assert alpha_cross == []
        assert beta_cross == []

    search_a = client.get(
        "/search",
        params={"q": "alphatokensecret", "mode": "keyword"},
        headers={WORKSPACE_HEADER: workspace_a},
    )
    search_b = client.get(
        "/search",
        params={"q": "alphatokensecret", "mode": "keyword"},
        headers={WORKSPACE_HEADER: workspace_b},
    )
    assert search_a.status_code == 200
    assert search_b.status_code == 200
    assert len(search_a.json()["results"]) == 1
    assert search_b.json()["results"] == []

    conversation_a = client.post("/conversations", headers={WORKSPACE_HEADER: workspace_a})
    conversation_b = client.post("/conversations", headers={WORKSPACE_HEADER: workspace_b})
    assert conversation_a.status_code == 201
    assert conversation_b.status_code == 201
    conversation_a_id = conversation_a.json()["conversation_id"]
    conversation_b_id = conversation_b.json()["conversation_id"]

    assert (
        client.get(
            f"/conversations/{conversation_a_id}",
            headers={WORKSPACE_HEADER: workspace_a},
        ).status_code
        == 200
    )
    assert (
        client.get(
            f"/conversations/{conversation_a_id}",
            headers={WORKSPACE_HEADER: workspace_b},
        ).status_code
        == 404
    )
    assert (
        client.get(
            f"/conversations/{conversation_b_id}",
            headers={WORKSPACE_HEADER: workspace_a},
        ).status_code
        == 404
    )
