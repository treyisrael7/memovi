"""HTTP + SQLAlchemy coverage for shipped workspace membership APIs."""

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
from memovi_shared import DEFAULT_WORKSPACE_ID, WorkspaceId
from memovi_workspace.api.dependencies import get_database_session as get_workspace_database_session
from memovi_workspace.infrastructure.persistence import Base as WorkspaceBase
from memovi_workspace.infrastructure.persistence.models import WorkspaceRecord
from memovi_workspace.infrastructure.repositories import SqlAlchemyWorkspaceMembershipRepository
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

MISSING_WORKSPACE_ID = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
OWNER_EMAIL = "workspace-owner@example.com"
MEMBER_EMAIL = "workspace-member@example.com"


@pytest.fixture
def membership_clients() -> Iterator[tuple[TestClient, TestClient, Engine]]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    AuthBase.metadata.create_all(engine)
    WorkspaceBase.metadata.create_all(engine)
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
    app.dependency_overrides[get_workspace_database_session] = database_session

    owner = TestClient(app, base_url="https://testserver")
    member = TestClient(app, base_url="https://testserver")
    try:
        owner_register = owner.post(
            "/auth/register",
            json={"email": OWNER_EMAIL, "password": "password123"},
        )
        member_register = member.post(
            "/auth/register",
            json={"email": MEMBER_EMAIL, "password": "password123"},
        )
        assert owner_register.status_code == 201
        assert member_register.status_code == 201
        yield owner, member, engine
    finally:
        owner.close()
        member.close()
        engine.dispose()


def _create_team(owner: TestClient, *, name: str = "Team") -> str:
    response = owner.post("/workspaces", json={"name": name})
    assert response.status_code == 201
    payload = response.json()
    assert payload["name"] == name
    assert payload["role"] == "owner"
    return str(payload["id"])


def _persisted_memberships(
    engine: Engine,
    workspace_id: str,
) -> dict[str, str]:
    with Session(engine) as session:
        repository = SqlAlchemyWorkspaceMembershipRepository(session)
        return {
            item.user_id: item.role
            for item in repository.list_for_workspace(WorkspaceId(workspace_id))
        }


def test_membership_endpoints_require_authentication(
    membership_clients: tuple[TestClient, TestClient, Engine],
) -> None:
    owner, _member, _engine = membership_clients
    workspace_id = _create_team(owner)
    anonymous = TestClient(owner.app, base_url="https://testserver")
    listed = anonymous.get(f"/workspaces/{workspace_id}/members")
    invited = anonymous.post(
        f"/workspaces/{workspace_id}/members",
        json={"email": MEMBER_EMAIL},
    )
    assert listed.status_code == 401
    assert invited.status_code == 401


def test_invite_list_remove_and_protected_owner_rules(
    membership_clients: tuple[TestClient, TestClient, Engine],
) -> None:
    owner, member, engine = membership_clients
    owner_id = owner.get("/auth/me").json()["id"]
    member_id = member.get("/auth/me").json()["id"]
    workspace_id = _create_team(owner)

    invited = owner.post(
        f"/workspaces/{workspace_id}/members",
        json={"email": MEMBER_EMAIL},
    )
    assert invited.status_code == 201
    invited_body = invited.json()
    assert invited_body["workspace_id"] == workspace_id
    assert invited_body["user_id"] == member_id
    assert invited_body["role"] == "member"
    assert invited_body["email"] == MEMBER_EMAIL

    listed = owner.get(f"/workspaces/{workspace_id}/members")
    assert listed.status_code == 200
    body = listed.json()
    assert body["count"] == 2
    by_user = {item["user_id"]: item for item in body["items"]}
    assert by_user[owner_id]["role"] == "owner"
    assert by_user[owner_id]["email"] == OWNER_EMAIL
    assert by_user[member_id]["role"] == "member"
    assert by_user[member_id]["email"] == MEMBER_EMAIL

    persisted = _persisted_memberships(engine, workspace_id)
    assert persisted == {owner_id: "owner", member_id: "member"}

    duplicate = owner.post(
        f"/workspaces/{workspace_id}/members",
        json={"email": MEMBER_EMAIL},
    )
    assert duplicate.status_code == 409
    assert "already a member" in duplicate.json()["detail"]

    unknown = owner.post(
        f"/workspaces/{workspace_id}/members",
        json={"email": "nobody@example.com"},
    )
    assert unknown.status_code == 404
    assert "No registered user found" in unknown.json()["detail"]

    member_invite = member.post(
        f"/workspaces/{workspace_id}/members",
        json={"email": OWNER_EMAIL},
    )
    assert member_invite.status_code == 403

    missing_workspace = owner.get(f"/workspaces/{MISSING_WORKSPACE_ID}/members")
    assert missing_workspace.status_code == 404

    sole_owner_leave = owner.post(f"/workspaces/{workspace_id}/leave")
    assert sole_owner_leave.status_code == 403
    assert "Transfer ownership before leaving" in sole_owner_leave.json()["detail"]

    last_owner_remove = owner.delete(f"/workspaces/{workspace_id}/members/{owner_id}")
    assert last_owner_remove.status_code == 403
    assert "Cannot remove the last owner" in last_owner_remove.json()["detail"]

    removed = owner.delete(f"/workspaces/{workspace_id}/members/{member_id}")
    assert removed.status_code == 200
    assert removed.json()["user_id"] == member_id
    assert removed.json()["role"] == "member"

    assert _persisted_memberships(engine, workspace_id) == {owner_id: "owner"}
    forbidden = member.get(f"/workspaces/{workspace_id}")
    assert forbidden.status_code == 403
    missing_member = owner.delete(f"/workspaces/{workspace_id}/members/{member_id}")
    assert missing_member.status_code == 404


def test_member_can_leave_and_owner_can_transfer(
    membership_clients: tuple[TestClient, TestClient, Engine],
) -> None:
    owner, member, engine = membership_clients
    owner_id = owner.get("/auth/me").json()["id"]
    member_id = member.get("/auth/me").json()["id"]
    workspace_id = _create_team(owner, name="Transfer Team")
    invited = owner.post(
        f"/workspaces/{workspace_id}/members",
        json={"email": MEMBER_EMAIL},
    )
    assert invited.status_code == 201

    left = member.post(f"/workspaces/{workspace_id}/leave")
    assert left.status_code == 200
    assert left.json()["user_id"] == member_id
    assert left.json()["role"] == "member"
    assert _persisted_memberships(engine, workspace_id) == {owner_id: "owner"}
    assert member.get(f"/workspaces/{workspace_id}").status_code == 403

    reinvite = owner.post(
        f"/workspaces/{workspace_id}/members",
        json={"email": MEMBER_EMAIL},
    )
    assert reinvite.status_code == 201

    transferred = owner.post(
        f"/workspaces/{workspace_id}/transfer-ownership",
        json={"new_owner_user_id": member_id},
    )
    assert transferred.status_code == 200
    payload = transferred.json()
    assert payload["previous_owner"]["user_id"] == owner_id
    assert payload["previous_owner"]["role"] == "member"
    assert payload["new_owner"]["user_id"] == member_id
    assert payload["new_owner"]["role"] == "owner"
    assert payload["new_owner"]["email"] == MEMBER_EMAIL

    persisted = _persisted_memberships(engine, workspace_id)
    assert persisted == {owner_id: "member", member_id: "owner"}

    assert (
        owner.post(
            f"/workspaces/{workspace_id}/members",
            json={"email": OWNER_EMAIL},
        ).status_code
        == 403
    )
    listed = member.get(f"/workspaces/{workspace_id}/members")
    assert listed.status_code == 200
    roles = {item["user_id"]: item["role"] for item in listed.json()["items"]}
    assert roles == persisted

    self_transfer = member.post(
        f"/workspaces/{workspace_id}/transfer-ownership",
        json={"new_owner_user_id": member_id},
    )
    assert self_transfer.status_code == 404
    assert "different member" in self_transfer.json()["detail"]


def test_membership_operations_cannot_cross_workspaces(
    membership_clients: tuple[TestClient, TestClient, Engine],
) -> None:
    owner, member, engine = membership_clients
    owner_id = owner.get("/auth/me").json()["id"]
    member_id = member.get("/auth/me").json()["id"]
    workspace_a = _create_team(owner, name="Alpha")
    workspace_b = _create_team(member, name="Beta")
    invited = owner.post(
        f"/workspaces/{workspace_a}/members",
        json={"email": MEMBER_EMAIL},
    )
    assert invited.status_code == 201

    alpha_members = owner.get(f"/workspaces/{workspace_a}/members").json()
    beta_members = member.get(f"/workspaces/{workspace_b}/members").json()
    assert {item["user_id"] for item in alpha_members["items"]} == {owner_id, member_id}
    assert {item["user_id"] for item in beta_members["items"]} == {member_id}

    assert owner.get(f"/workspaces/{workspace_b}/members").status_code == 403
    assert owner.delete(f"/workspaces/{workspace_b}/members/{member_id}").status_code == 403
    assert (
        owner.post(
            f"/workspaces/{workspace_b}/transfer-ownership",
            json={"new_owner_user_id": owner_id},
        ).status_code
        == 403
    )

    assert _persisted_memberships(engine, workspace_b) == {member_id: "owner"}
    assert _persisted_memberships(engine, workspace_a) == {
        owner_id: "owner",
        member_id: "member",
    }
