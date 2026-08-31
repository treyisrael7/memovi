"""HTTP + SQLAlchemy coverage for Chat citation GET /memory/by-document/{id}."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime

import pytest
from api.app import create_app
from api.database import database_session as api_database_session
from api.document_processing import configure_document_processing
from auth.api.dependencies import get_database_session as get_auth_database_session
from auth.infrastructure.persistence import Base as AuthBase
from documents.infrastructure.queue import NoOpProcessingJobQueue
from documents.infrastructure.storage import InMemoryObjectStorage
from fastapi.testclient import TestClient
from memovi_memory.api.dependencies import get_database_session as get_memory_database_session
from memovi_memory.domain.entities import KnowledgeItem
from memovi_memory.infrastructure.persistence.models import Base as MemoryBase
from memovi_memory.infrastructure.repositories import SqlAlchemyKnowledgeRepository
from memovi_shared import DEFAULT_WORKSPACE_ID, WorkspaceId
from memovi_workspace.api.dependencies import get_database_session as get_workspace_database_session
from memovi_workspace.infrastructure.persistence import Base as WorkspaceBase
from memovi_workspace.infrastructure.persistence.models import WorkspaceRecord
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

WORKSPACE_HEADER = "X-Memovi-Workspace-Id"
DOCUMENT_A_ID = "3b96152e-5ba9-4933-8819-2a08069a6d9f"
DOCUMENT_B_ID = "4c07263f-6cba-5a44-9920-3b19170b7e80"
VERSION_A_DEFAULT = "7d086319-ee8e-4fe5-9fc3-30eddad79749"
VERSION_B_DEFAULT = "8e19742a-ff9f-5af6-a0d4-41feebc8a85a"
VERSION_A_OTHER = "9f20853b-0a0a-6b07-b1e5-52ff0cd9b96b"


def _headers(workspace_id: str = DEFAULT_WORKSPACE_ID.value) -> dict[str, str]:
    return {WORKSPACE_HEADER: workspace_id}


@pytest.fixture
def by_document_client() -> Iterator[tuple[TestClient, Engine]]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    AuthBase.metadata.create_all(engine)
    WorkspaceBase.metadata.create_all(engine)
    MemoryBase.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)

    with Session(engine) as seed_session:
        seed_session.add(
            WorkspaceRecord(
                id=DEFAULT_WORKSPACE_ID.value,
                name="Default",
                created_at=datetime(2026, 1, 1, tzinfo=UTC),
            )
        )
        seed_session.commit()

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

    app = create_app()
    app.state.auth_session_factory = session_factory
    configure_document_processing(
        app,
        session_factory=session_factory,
        queue=NoOpProcessingJobQueue(),
        object_storage=InMemoryObjectStorage(),
    )
    app.dependency_overrides[api_database_session] = database_session
    app.dependency_overrides[get_auth_database_session] = database_session
    app.dependency_overrides[get_memory_database_session] = database_session
    app.dependency_overrides[get_workspace_database_session] = database_session

    client = TestClient(app, base_url="https://testserver")
    try:
        register_response = client.post(
            "/auth/register",
            json={"email": "citation-by-document@example.com", "password": "password123"},
        )
        assert register_response.status_code == 201
        yield client, engine
    finally:
        client.close()
        engine.dispose()


def _save_knowledge(
    engine: Engine,
    *,
    workspace_id: WorkspaceId,
    document_id: str,
    document_version_id: str,
) -> KnowledgeItem:
    item = KnowledgeItem.create(
        workspace_id=workspace_id,
        document_id=document_id,
        document_version_id=document_version_id,
        source_type="upload",
        mime_type="text/markdown",
        now=datetime(2026, 8, 31, 12, 0, tzinfo=UTC),
    )
    with Session(engine) as session:
        SqlAlchemyKnowledgeRepository(session).save(item)
        session.commit()
    return item


def test_memory_by_document_returns_persisted_workspace_scoped_knowledge(
    by_document_client: tuple[TestClient, Engine],
) -> None:
    client, engine = by_document_client
    other_workspace = client.post("/workspaces", json={"name": "Other"})
    assert other_workspace.status_code == 201
    other_workspace_id = WorkspaceId(other_workspace.json()["id"])

    default_a = _save_knowledge(
        engine,
        workspace_id=DEFAULT_WORKSPACE_ID,
        document_id=DOCUMENT_A_ID,
        document_version_id=VERSION_A_DEFAULT,
    )
    default_b = _save_knowledge(
        engine,
        workspace_id=DEFAULT_WORKSPACE_ID,
        document_id=DOCUMENT_B_ID,
        document_version_id=VERSION_B_DEFAULT,
    )
    other_a = _save_knowledge(
        engine,
        workspace_id=other_workspace_id,
        document_id=DOCUMENT_A_ID,
        document_version_id=VERSION_A_OTHER,
    )

    default_a_response = client.get(
        f"/memory/by-document/{DOCUMENT_A_ID}",
        headers=_headers(),
    )
    assert default_a_response.status_code == 200
    default_a_body = default_a_response.json()
    assert default_a_body["count"] == 1
    assert default_a_body["items"][0]["id"] == default_a.id.value
    assert default_a_body["items"][0]["document_id"] == DOCUMENT_A_ID
    assert default_a_body["items"][0]["workspace_id"] == DEFAULT_WORKSPACE_ID.value
    assert default_b.id.value not in {item["id"] for item in default_a_body["items"]}
    assert other_a.id.value not in {item["id"] for item in default_a_body["items"]}

    default_b_response = client.get(
        f"/memory/by-document/{DOCUMENT_B_ID}",
        headers=_headers(),
    )
    assert default_b_response.status_code == 200
    assert default_b_response.json()["count"] == 1
    assert default_b_response.json()["items"][0]["id"] == default_b.id.value

    other_a_response = client.get(
        f"/memory/by-document/{DOCUMENT_A_ID}",
        headers=_headers(other_workspace_id.value),
    )
    assert other_a_response.status_code == 200
    other_a_body = other_a_response.json()
    assert other_a_body["count"] == 1
    assert other_a_body["items"][0]["id"] == other_a.id.value
    assert other_a_body["items"][0]["workspace_id"] == other_workspace_id.value

    other_b_response = client.get(
        f"/memory/by-document/{DOCUMENT_B_ID}",
        headers=_headers(other_workspace_id.value),
    )
    assert other_b_response.status_code == 200
    assert other_b_response.json() == {"items": [], "count": 0}

    with Session(engine) as session:
        repository = SqlAlchemyKnowledgeRepository(session)
        persisted_default_a = repository.list_by_document(
            workspace_id=DEFAULT_WORKSPACE_ID,
            document_id=DOCUMENT_A_ID,
        )
        persisted_other_a = repository.list_by_document(
            workspace_id=other_workspace_id,
            document_id=DOCUMENT_A_ID,
        )
        assert [item.id for item in persisted_default_a] == [default_a.id]
        assert [item.id for item in persisted_other_a] == [other_a.id]
