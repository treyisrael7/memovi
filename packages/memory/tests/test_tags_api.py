"""HTTP + SQLAlchemy coverage for the shipped Tags API."""

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
from memovi_memory.domain.value_objects import CollectionMemberKind, TagId
from memovi_memory.infrastructure.persistence.models import Base as MemoryBase
from memovi_memory.infrastructure.repositories import SqlAlchemyTagRepository
from memovi_shared import DEFAULT_WORKSPACE_ID, WorkspaceId
from memovi_workspace.api.dependencies import get_database_session as get_workspace_database_session
from memovi_workspace.infrastructure.persistence import Base as WorkspaceBase
from memovi_workspace.infrastructure.persistence.models import WorkspaceRecord
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

WORKSPACE_HEADER = "X-Memovi-Workspace-Id"
DOCUMENT_ID = "3b96152e-5ba9-4933-8819-2a08069a6d9f"
MISSING_TAG_ID = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"


def _headers(workspace_id: str = DEFAULT_WORKSPACE_ID.value) -> dict[str, str]:
    return {WORKSPACE_HEADER: workspace_id}


@pytest.fixture
def tags_client() -> Iterator[tuple[TestClient, Engine]]:
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
            json={"email": "tags-tester@example.com", "password": "password123"},
        )
        assert register_response.status_code == 201
        yield client, engine
    finally:
        client.close()
        engine.dispose()


def test_tags_require_authentication(tags_client: tuple[TestClient, Engine]) -> None:
    client, _engine = tags_client
    client.cookies.clear()
    response = client.get("/tags", headers=_headers())
    assert response.status_code == 401


def test_tag_lifecycle_persists_assignments_through_sqlalchemy(
    tags_client: tuple[TestClient, Engine],
) -> None:
    client, engine = tags_client
    workspace_id = DEFAULT_WORKSPACE_ID.value
    headers = _headers(workspace_id)

    created = client.post(
        "/tags",
        headers=headers,
        json={"name": "  Research  ", "color": "  #336699  ", "description": " Papers "},
    )
    assert created.status_code == 201
    payload = created.json()
    tag_id = payload["id"]
    assert payload["name"] == "Research"
    assert payload["color"] == "#336699"
    assert payload["description"] == "Papers"
    assert payload["workspace_id"] == workspace_id

    notes = client.post("/tags", headers=headers, json={"name": "Notes"})
    assert notes.status_code == 201

    listed = client.get("/tags", headers=headers)
    assert listed.status_code == 200
    listed_body = listed.json()
    assert listed_body["count"] == 2
    names = {item["name"] for item in listed_body["items"]}
    assert names == {"Notes", "Research"}

    suggestions = client.get("/tags/suggest", headers=headers, params={"q": "re"})
    assert suggestions.status_code == 200
    assert [item["name"] for item in suggestions.json()["items"]] == ["Research"]

    fetched = client.get(f"/tags/{tag_id}", headers=headers)
    assert fetched.status_code == 200
    assert fetched.json()["name"] == "Research"

    updated = client.patch(
        f"/tags/{tag_id}",
        headers=headers,
        json={"name": "Archive", "color": "#111111", "description": "Inactive"},
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "Archive"
    assert updated.json()["color"] == "#111111"
    assert updated.json()["description"] == "Inactive"

    assigned = client.post(
        f"/tags/{tag_id}/assignments",
        headers=headers,
        json={"member_kind": "document", "member_id": DOCUMENT_ID},
    )
    assert assigned.status_code == 201
    assignment = assigned.json()
    assert assignment["tag_id"] == tag_id
    assert assignment["member_kind"] == "document"
    assert assignment["member_id"] == DOCUMENT_ID

    duplicate = client.post(
        f"/tags/{tag_id}/assignments",
        headers=headers,
        json={"member_kind": "document", "member_id": DOCUMENT_ID},
    )
    assert duplicate.status_code == 409

    assignments = client.get(f"/tags/{tag_id}/assignments", headers=headers)
    assert assignments.status_code == 200
    assignments_body = assignments.json()
    assert assignments_body["count"] == 1
    assert assignments_body["items"][0]["member_id"] == DOCUMENT_ID

    for_target = client.get(
        "/tags/for-target",
        headers=headers,
        params={"member_kind": "document", "member_id": DOCUMENT_ID},
    )
    assert for_target.status_code == 200
    assert [item["id"] for item in for_target.json()["items"]] == [tag_id]

    listed_after = client.get("/tags", headers=headers).json()
    archive = next(item for item in listed_after["items"] if item["id"] == tag_id)
    assert archive["assignment_count"] == 1
    assert archive["counts_by_kind"]["document"] == 1

    with Session(engine) as session:
        repository = SqlAlchemyTagRepository(session)
        persisted = repository.get_by_id(TagId(tag_id), workspace_id=WorkspaceId(workspace_id))
        assert persisted is not None
        assert persisted.name == "Archive"
        assert persisted.color == "#111111"
        assert persisted.description == "Inactive"
        stored = repository.list_assignments(
            TagId(tag_id),
            workspace_id=WorkspaceId(workspace_id),
        )
        assert len(stored) == 1
        assert stored[0].member_kind == CollectionMemberKind.DOCUMENT
        assert stored[0].member_id == DOCUMENT_ID

    unassigned = client.delete(
        f"/tags/{tag_id}/assignments/document/{DOCUMENT_ID}",
        headers=headers,
    )
    assert unassigned.status_code == 204

    with Session(engine) as session:
        repository = SqlAlchemyTagRepository(session)
        assert (
            repository.get_assignment(
                tag_id=TagId(tag_id),
                member_kind=CollectionMemberKind.DOCUMENT,
                member_id=DOCUMENT_ID,
                workspace_id=WorkspaceId(workspace_id),
            )
            is None
        )

    deleted = client.delete(f"/tags/{tag_id}", headers=headers)
    assert deleted.status_code == 204
    assert client.get(f"/tags/{tag_id}", headers=headers).status_code == 404

    with Session(engine) as session:
        repository = SqlAlchemyTagRepository(session)
        assert repository.get_by_id(TagId(tag_id), workspace_id=WorkspaceId(workspace_id)) is None
        remaining = repository.list_by_workspace(workspace_id=WorkspaceId(workspace_id))
        assert [tag.name for tag in remaining] == ["Notes"]


def test_tags_reject_invalid_name_duplicate_and_unknown_id(
    tags_client: tuple[TestClient, Engine],
) -> None:
    client, _engine = tags_client
    headers = _headers()

    blank = client.post("/tags", headers=headers, json={"name": "   "})
    assert blank.status_code == 422
    assert blank.json()["detail"] == "Tag name is required."

    created = client.post("/tags", headers=headers, json={"name": "Research"})
    assert created.status_code == 201
    duplicate = client.post("/tags", headers=headers, json={"name": "research"})
    assert duplicate.status_code == 409

    missing = client.get(f"/tags/{MISSING_TAG_ID}", headers=headers)
    assert missing.status_code == 404

    bad_kind = client.post(
        f"/tags/{created.json()['id']}/assignments",
        headers=headers,
        json={"member_kind": "notebook", "member_id": DOCUMENT_ID},
    )
    assert bad_kind.status_code == 422


def test_tags_are_isolated_by_workspace(tags_client: tuple[TestClient, Engine]) -> None:
    client, engine = tags_client
    default_headers = _headers()
    other_workspace = client.post("/workspaces", json={"name": "Other"})
    assert other_workspace.status_code == 201
    other_id = other_workspace.json()["id"]
    other_headers = _headers(other_id)

    in_default = client.post("/tags", headers=default_headers, json={"name": "DefaultTag"})
    assert in_default.status_code == 201
    default_tag_id = in_default.json()["id"]

    in_other = client.post("/tags", headers=other_headers, json={"name": "OtherTag"})
    assert in_other.status_code == 201
    other_tag_id = in_other.json()["id"]

    default_list = client.get("/tags", headers=default_headers).json()
    other_list = client.get("/tags", headers=other_headers).json()
    assert {item["id"] for item in default_list["items"]} == {default_tag_id}
    assert {item["id"] for item in other_list["items"]} == {other_tag_id}

    assert client.get(f"/tags/{default_tag_id}", headers=other_headers).status_code == 404
    assert (
        client.patch(
            f"/tags/{default_tag_id}",
            headers=other_headers,
            json={"name": "Hijacked"},
        ).status_code
        == 404
    )
    assert client.delete(f"/tags/{default_tag_id}", headers=other_headers).status_code == 404

    with Session(engine) as session:
        repository = SqlAlchemyTagRepository(session)
        assert (
            repository.get_by_id(TagId(default_tag_id), workspace_id=WorkspaceId(other_id)) is None
        )
        owned = repository.get_by_id(TagId(default_tag_id), workspace_id=DEFAULT_WORKSPACE_ID)
        assert owned is not None
        assert owned.name == "DefaultTag"
        other_owned = repository.get_by_id(TagId(other_tag_id), workspace_id=WorkspaceId(other_id))
        assert other_owned is not None
        assert other_owned.workspace_id.value == other_id
