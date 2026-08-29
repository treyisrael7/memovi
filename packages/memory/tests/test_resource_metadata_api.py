"""HTTP + SQLAlchemy coverage for the shipped Resource Metadata API."""

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
from memovi_memory.domain.value_objects import CollectionMemberKind
from memovi_memory.infrastructure.persistence.models import Base as MemoryBase
from memovi_memory.infrastructure.repositories import SqlAlchemyResourceMetadataRepository
from memovi_shared import DEFAULT_WORKSPACE_ID, WorkspaceId
from memovi_workspace.api.dependencies import get_database_session as get_workspace_database_session
from memovi_workspace.infrastructure.persistence import Base as WorkspaceBase
from memovi_workspace.infrastructure.persistence.models import WorkspaceRecord
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

WORKSPACE_HEADER = "X-Memovi-Workspace-Id"
DOCUMENT_ID = "3b96152e-5ba9-4933-8819-2a08069a6d9f"
METADATA_PATH = f"/resource-metadata/document/{DOCUMENT_ID}"


def _headers(workspace_id: str = DEFAULT_WORKSPACE_ID.value) -> dict[str, str]:
    return {WORKSPACE_HEADER: workspace_id}


@pytest.fixture
def metadata_client() -> Iterator[tuple[TestClient, Engine]]:
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
            json={"email": "resource-metadata-tester@example.com", "password": "password123"},
        )
        assert register_response.status_code == 201
        yield client, engine
    finally:
        client.close()
        engine.dispose()


def test_resource_metadata_requires_authentication(
    metadata_client: tuple[TestClient, Engine],
) -> None:
    client, _engine = metadata_client
    client.cookies.clear()
    response = client.get(METADATA_PATH, headers=_headers())
    assert response.status_code == 401


def test_resource_metadata_upsert_and_get_persist_through_sqlalchemy(
    metadata_client: tuple[TestClient, Engine],
) -> None:
    client, engine = metadata_client
    workspace_id = DEFAULT_WORKSPACE_ID.value
    headers = _headers(workspace_id)

    missing = client.get(METADATA_PATH, headers=headers)
    assert missing.status_code == 404

    created = client.put(
        METADATA_PATH,
        headers=headers,
        json={"title": " Brief ", "description": " Overview ", "notes": " Keep "},
    )
    assert created.status_code == 200
    payload = created.json()
    assert payload["workspace_id"] == workspace_id
    assert payload["member_kind"] == "document"
    assert payload["member_id"] == DOCUMENT_ID
    assert payload["title"] == "Brief"
    assert payload["description"] == "Overview"
    assert payload["notes"] == "Keep"
    assert payload["updated_at"]

    fetched = client.get(METADATA_PATH, headers=headers)
    assert fetched.status_code == 200
    fetched_body = fetched.json()
    assert fetched_body["title"] == "Brief"
    assert fetched_body["description"] == "Overview"
    assert fetched_body["notes"] == "Keep"
    assert fetched_body["workspace_id"] == workspace_id
    assert fetched_body["member_kind"] == "document"
    assert fetched_body["member_id"] == DOCUMENT_ID

    with Session(engine) as session:
        repository = SqlAlchemyResourceMetadataRepository(session)
        persisted = repository.get(
            workspace_id=WorkspaceId(workspace_id),
            member_kind=CollectionMemberKind.DOCUMENT,
            member_id=DOCUMENT_ID,
        )
        assert persisted is not None
        assert persisted.workspace_id.value == workspace_id
        assert persisted.member_kind == CollectionMemberKind.DOCUMENT
        assert persisted.member_id == DOCUMENT_ID
        assert persisted.title == "Brief"
        assert persisted.description == "Overview"
        assert persisted.notes == "Keep"

    updated = client.put(
        METADATA_PATH,
        headers=headers,
        json={"title": "Revised", "description": None, "notes": "Updated notes"},
    )
    assert updated.status_code == 200
    updated_body = updated.json()
    assert updated_body["title"] == "Revised"
    assert updated_body["description"] is None
    assert updated_body["notes"] == "Updated notes"

    blanked = client.put(
        METADATA_PATH,
        headers=headers,
        json={"title": "  ", "description": "Kept", "notes": ""},
    )
    assert blanked.status_code == 200
    blanked_body = blanked.json()
    assert blanked_body["title"] is None
    assert blanked_body["description"] == "Kept"
    assert blanked_body["notes"] is None

    with Session(engine) as session:
        repository = SqlAlchemyResourceMetadataRepository(session)
        stored = repository.get(
            workspace_id=WorkspaceId(workspace_id),
            member_kind=CollectionMemberKind.DOCUMENT,
            member_id=DOCUMENT_ID,
        )
        assert stored is not None
        assert stored.member_id == DOCUMENT_ID
        assert stored.member_kind == CollectionMemberKind.DOCUMENT
        assert stored.workspace_id.value == workspace_id
        assert stored.title is None
        assert stored.description == "Kept"
        assert stored.notes is None


def test_resource_metadata_rejects_invalid_kind_payload_and_unknown_resource(
    metadata_client: tuple[TestClient, Engine],
) -> None:
    client, _engine = metadata_client
    headers = _headers()

    unknown = client.get(METADATA_PATH, headers=headers)
    assert unknown.status_code == 404

    invalid_kind_get = client.get(
        f"/resource-metadata/notebook/{DOCUMENT_ID}",
        headers=headers,
    )
    assert invalid_kind_get.status_code == 422

    invalid_kind_put = client.put(
        f"/resource-metadata/notebook/{DOCUMENT_ID}",
        headers=headers,
        json={"title": "Nope"},
    )
    assert invalid_kind_put.status_code == 422

    too_long = client.put(
        METADATA_PATH,
        headers=headers,
        json={"title": "x" * 513},
    )
    assert too_long.status_code == 422

    blank_member = client.put(
        "/resource-metadata/document/%20",
        headers=headers,
        json={"title": "Untitled"},
    )
    assert blank_member.status_code == 422
    assert blank_member.json()["detail"] == "Member ID is required."


def test_resource_metadata_is_isolated_by_workspace(
    metadata_client: tuple[TestClient, Engine],
) -> None:
    client, engine = metadata_client
    default_headers = _headers()
    other_workspace = client.post("/workspaces", json={"name": "Other"})
    assert other_workspace.status_code == 201
    other_id = other_workspace.json()["id"]
    other_headers = _headers(other_id)

    created = client.put(
        METADATA_PATH,
        headers=default_headers,
        json={"title": "Default title", "description": "Owned notes", "notes": "Keep"},
    )
    assert created.status_code == 200

    assert client.get(METADATA_PATH, headers=other_headers).status_code == 404

    other_put = client.put(
        METADATA_PATH,
        headers=other_headers,
        json={"title": "Hijacked", "description": "Other workspace", "notes": "Steal"},
    )
    assert other_put.status_code == 200
    assert other_put.json()["workspace_id"] == other_id
    assert other_put.json()["title"] == "Hijacked"

    default_again = client.get(METADATA_PATH, headers=default_headers)
    assert default_again.status_code == 200
    default_body = default_again.json()
    assert default_body["workspace_id"] == DEFAULT_WORKSPACE_ID.value
    assert default_body["title"] == "Default title"
    assert default_body["description"] == "Owned notes"
    assert default_body["notes"] == "Keep"

    assert client.delete(METADATA_PATH, headers=other_headers).status_code == 405

    with Session(engine) as session:
        repository = SqlAlchemyResourceMetadataRepository(session)
        assert (
            repository.get(
                workspace_id=WorkspaceId(other_id),
                member_kind=CollectionMemberKind.DOCUMENT,
                member_id=DOCUMENT_ID,
            )
            is not None
        )
        owned = repository.get(
            workspace_id=DEFAULT_WORKSPACE_ID,
            member_kind=CollectionMemberKind.DOCUMENT,
            member_id=DOCUMENT_ID,
        )
        assert owned is not None
        assert owned.workspace_id.value == DEFAULT_WORKSPACE_ID.value
        assert owned.title == "Default title"
        assert owned.description == "Owned notes"
        assert owned.notes == "Keep"
        other_owned = repository.get(
            workspace_id=WorkspaceId(other_id),
            member_kind=CollectionMemberKind.DOCUMENT,
            member_id=DOCUMENT_ID,
        )
        assert other_owned is not None
        assert other_owned.workspace_id.value == other_id
        assert other_owned.title == "Hijacked"
