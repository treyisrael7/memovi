"""HTTP + SQLAlchemy coverage for the shipped Collections API."""

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
from memovi_memory.domain.value_objects import CollectionId, CollectionMemberKind
from memovi_memory.infrastructure.persistence.models import Base as MemoryBase
from memovi_memory.infrastructure.repositories import SqlAlchemyCollectionRepository
from memovi_shared import DEFAULT_WORKSPACE_ID, WorkspaceId
from memovi_workspace.api.dependencies import get_database_session as get_workspace_database_session
from memovi_workspace.infrastructure.persistence import Base as WorkspaceBase
from memovi_workspace.infrastructure.persistence.models import WorkspaceRecord
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

WORKSPACE_HEADER = "X-Memovi-Workspace-Id"
DOCUMENT_ID = "3b96152e-5ba9-4933-8819-2a08069a6d9f"
MISSING_COLLECTION_ID = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"


def _headers(workspace_id: str = DEFAULT_WORKSPACE_ID.value) -> dict[str, str]:
    return {WORKSPACE_HEADER: workspace_id}


@pytest.fixture
def collections_client() -> Iterator[tuple[TestClient, Engine]]:
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
            json={"email": "collections-tester@example.com", "password": "password123"},
        )
        assert register_response.status_code == 201
        yield client, engine
    finally:
        client.close()
        engine.dispose()


def test_collections_require_authentication(collections_client: tuple[TestClient, Engine]) -> None:
    client, _engine = collections_client
    client.cookies.clear()
    response = client.get("/collections", headers=_headers())
    assert response.status_code == 401


def test_collection_lifecycle_persists_through_sqlalchemy(
    collections_client: tuple[TestClient, Engine],
) -> None:
    client, engine = collections_client
    workspace_id = DEFAULT_WORKSPACE_ID.value
    headers = _headers(workspace_id)

    created = client.post(
        "/collections",
        headers=headers,
        json={"name": "  Research  ", "description": " Papers "},
    )
    assert created.status_code == 201
    payload = created.json()
    collection_id = payload["id"]
    assert payload["name"] == "Research"
    assert payload["description"] == "Papers"
    assert payload["workspace_id"] == workspace_id

    listed = client.get("/collections", headers=headers)
    assert listed.status_code == 200
    listed_body = listed.json()
    assert listed_body["count"] == 1
    assert listed_body["items"][0]["id"] == collection_id
    assert listed_body["items"][0]["item_count"] == 0

    fetched = client.get(f"/collections/{collection_id}", headers=headers)
    assert fetched.status_code == 200
    assert fetched.json()["name"] == "Research"

    renamed = client.patch(
        f"/collections/{collection_id}",
        headers=headers,
        json={"name": "Work"},
    )
    assert renamed.status_code == 200
    assert renamed.json()["name"] == "Work"

    described = client.patch(
        f"/collections/{collection_id}/description",
        headers=headers,
        json={"description": "Active projects"},
    )
    assert described.status_code == 200
    assert described.json()["description"] == "Active projects"

    membership = client.post(
        f"/collections/{collection_id}/members",
        headers=headers,
        json={
            "member_kind": "document",
            "member_id": DOCUMENT_ID,
            "reason": "Primary brief",
        },
    )
    assert membership.status_code == 201
    membership_body = membership.json()
    assert membership_body["collection_id"] == collection_id
    assert membership_body["member_kind"] == "document"
    assert membership_body["member_id"] == DOCUMENT_ID
    assert membership_body["reason"] == "Primary brief"

    duplicate = client.post(
        f"/collections/{collection_id}/members",
        headers=headers,
        json={"member_kind": "document", "member_id": DOCUMENT_ID},
    )
    assert duplicate.status_code == 409

    members = client.get(f"/collections/{collection_id}/members", headers=headers)
    assert members.status_code == 200
    members_body = members.json()
    assert members_body["count"] == 1
    assert members_body["items"][0]["member_id"] == DOCUMENT_ID

    summary = client.get(f"/collections/{collection_id}/summary", headers=headers)
    assert summary.status_code == 200
    summary_body = summary.json()
    assert summary_body["item_count"] == 1
    assert summary_body["counts_by_kind"]["document"] == 1
    activity_types = {entry["activity_type"] for entry in summary_body["recent_activity"]}
    assert "created" in activity_types
    assert "member_added" in activity_types

    with Session(engine) as session:
        repository = SqlAlchemyCollectionRepository(session)
        persisted = repository.get_by_id(
            CollectionId(collection_id),
            workspace_id=WorkspaceId(workspace_id),
        )
        assert persisted is not None
        assert persisted.metadata.name == "Work"
        assert persisted.metadata.description == "Active projects"
        assert persisted.workspace_id.value == workspace_id
        stored_members = repository.list_memberships(
            CollectionId(collection_id),
            workspace_id=WorkspaceId(workspace_id),
        )
        assert len(stored_members) == 1
        assert stored_members[0].member_kind == CollectionMemberKind.DOCUMENT
        assert stored_members[0].member_id == DOCUMENT_ID
        assert stored_members[0].reason == "Primary brief"

    removed = client.delete(
        f"/collections/{collection_id}/members/document/{DOCUMENT_ID}",
        headers=headers,
    )
    assert removed.status_code == 204

    with Session(engine) as session:
        repository = SqlAlchemyCollectionRepository(session)
        assert (
            repository.get_membership(
                collection_id=CollectionId(collection_id),
                member_kind=CollectionMemberKind.DOCUMENT,
                member_id=DOCUMENT_ID,
                workspace_id=WorkspaceId(workspace_id),
            )
            is None
        )

    deleted = client.delete(f"/collections/{collection_id}", headers=headers)
    assert deleted.status_code == 204
    assert client.get(f"/collections/{collection_id}", headers=headers).status_code == 404

    with Session(engine) as session:
        repository = SqlAlchemyCollectionRepository(session)
        assert (
            repository.get_by_id(
                CollectionId(collection_id),
                workspace_id=WorkspaceId(workspace_id),
            )
            is None
        )
        assert (
            repository.list_memberships(
                CollectionId(collection_id),
                workspace_id=WorkspaceId(workspace_id),
            )
            == []
        )


def test_collections_reject_invalid_name_and_unknown_id(
    collections_client: tuple[TestClient, Engine],
) -> None:
    client, _engine = collections_client
    headers = _headers()

    blank = client.post("/collections", headers=headers, json={"name": "   "})
    assert blank.status_code == 422
    assert blank.json()["detail"] == "Collection name is required."

    missing = client.get(f"/collections/{MISSING_COLLECTION_ID}", headers=headers)
    assert missing.status_code == 404

    invalid_member = client.post(
        "/collections",
        headers=headers,
        json={"name": "Valid"},
    )
    collection_id = invalid_member.json()["id"]
    bad_kind = client.post(
        f"/collections/{collection_id}/members",
        headers=headers,
        json={"member_kind": "notebook", "member_id": DOCUMENT_ID},
    )
    assert bad_kind.status_code == 422


def test_collections_are_isolated_by_workspace(
    collections_client: tuple[TestClient, Engine],
) -> None:
    client, engine = collections_client
    default_headers = _headers()
    other_workspace = client.post("/workspaces", json={"name": "Other"})
    assert other_workspace.status_code == 201
    other_id = other_workspace.json()["id"]
    other_headers = _headers(other_id)

    in_default = client.post(
        "/collections",
        headers=default_headers,
        json={"name": "Default notes"},
    )
    assert in_default.status_code == 201
    default_collection_id = in_default.json()["id"]

    in_other = client.post(
        "/collections",
        headers=other_headers,
        json={"name": "Other notes"},
    )
    assert in_other.status_code == 201
    other_collection_id = in_other.json()["id"]

    default_list = client.get("/collections", headers=default_headers).json()
    other_list = client.get("/collections", headers=other_headers).json()
    assert {item["id"] for item in default_list["items"]} == {default_collection_id}
    assert {item["id"] for item in other_list["items"]} == {other_collection_id}

    assert (
        client.get(f"/collections/{default_collection_id}", headers=other_headers).status_code
        == 404
    )
    assert (
        client.patch(
            f"/collections/{default_collection_id}",
            headers=other_headers,
            json={"name": "Hijacked"},
        ).status_code
        == 404
    )
    assert (
        client.delete(f"/collections/{default_collection_id}", headers=other_headers).status_code
        == 404
    )

    with Session(engine) as session:
        repository = SqlAlchemyCollectionRepository(session)
        assert (
            repository.get_by_id(
                CollectionId(default_collection_id),
                workspace_id=WorkspaceId(other_id),
            )
            is None
        )
        owned = repository.get_by_id(
            CollectionId(default_collection_id),
            workspace_id=DEFAULT_WORKSPACE_ID,
        )
        assert owned is not None
        assert owned.metadata.name == "Default notes"
        other_owned = repository.get_by_id(
            CollectionId(other_collection_id),
            workspace_id=WorkspaceId(other_id),
        )
        assert other_owned is not None
        assert other_owned.workspace_id.value == other_id
