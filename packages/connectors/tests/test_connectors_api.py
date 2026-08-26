"""HTTP + SQLAlchemy coverage for the shipped filesystem connector API."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

import pytest
from api.app import create_app
from api.database import database_session as api_database_session
from api.document_processing import configure_document_processing
from api.documents_session import build_documents_database_session
from auth.api.dependencies import get_database_session as get_auth_database_session
from auth.infrastructure.persistence import Base as AuthBase
from documents.api.dependencies import get_database_session as get_documents_database_session
from documents.infrastructure.persistence import Base as DocumentsBase
from documents.infrastructure.queue import NoOpProcessingJobQueue
from documents.infrastructure.storage import InMemoryObjectStorage
from fastapi.testclient import TestClient
from memovi_connectors.api.dependencies import (
    get_database_session as get_connectors_database_session,
)
from memovi_connectors.infrastructure.persistence.models import Base as ConnectorsBase
from memovi_connectors.infrastructure.repositories import SqlAlchemyFilesystemFolderRepository
from memovi_shared import DEFAULT_WORKSPACE_ID, WorkspaceId
from memovi_workspace.api.dependencies import get_database_session as get_workspace_database_session
from memovi_workspace.infrastructure.persistence import Base as WorkspaceBase
from memovi_workspace.infrastructure.persistence.models import WorkspaceRecord
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

WORKSPACE_HEADER = "X-Memovi-Workspace-Id"
MISSING_FOLDER_ID = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"


def _headers(workspace_id: str = DEFAULT_WORKSPACE_ID.value) -> dict[str, str]:
    return {WORKSPACE_HEADER: workspace_id}


@pytest.fixture
def connectors_client() -> Iterator[tuple[TestClient, Engine]]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    AuthBase.metadata.create_all(engine)
    WorkspaceBase.metadata.create_all(engine)
    DocumentsBase.metadata.create_all(engine)
    ConnectorsBase.metadata.create_all(engine)
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

    documents_session = build_documents_database_session(database_session)

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
    app.dependency_overrides[get_documents_database_session] = documents_session
    app.dependency_overrides[get_connectors_database_session] = documents_session

    client = TestClient(app, base_url="https://testserver")
    try:
        register_response = client.post(
            "/auth/register",
            json={"email": "connectors-tester@example.com", "password": "password123"},
        )
        assert register_response.status_code == 201
        yield client, engine
    finally:
        client.close()
        engine.dispose()


def _add_folder(
    client: TestClient,
    root: Path,
    *,
    workspace_id: str = DEFAULT_WORKSPACE_ID.value,
    display_name: str | None = "Notes",
) -> dict[str, object]:
    body: dict[str, object] = {"root_path": str(root)}
    if display_name is not None:
        body["display_name"] = display_name
    response = client.post(
        "/connectors/filesystem/folders",
        headers=_headers(workspace_id),
        json=body,
    )
    assert response.status_code == 201
    return response.json()


def test_connectors_require_authentication(
    connectors_client: tuple[TestClient, Engine],
) -> None:
    client, _engine = connectors_client
    client.cookies.clear()
    headers = _headers()
    listed = client.get("/connectors", headers=headers)
    folders = client.get("/connectors/filesystem/folders", headers=headers)
    health = client.get("/connectors/health", headers=headers)
    assert listed.status_code == 401
    assert folders.status_code == 401
    assert health.status_code == 401


def test_filesystem_folder_lifecycle_persists_and_syncs_through_http(
    connectors_client: tuple[TestClient, Engine],
    tmp_path: Path,
) -> None:
    client, engine = connectors_client
    workspace_id = DEFAULT_WORKSPACE_ID.value
    headers = _headers(workspace_id)
    (tmp_path / "notes.md").write_text("# Hello", encoding="utf-8")

    types = client.get("/connectors", headers=headers)
    assert types.status_code == 200
    types_body = types.json()
    assert types_body["count"] >= 1
    filesystem = next(item for item in types_body["items"] if item["connector_id"] == "filesystem")
    assert filesystem["display_name"] == "Filesystem"
    assert filesystem["source_category"] == "filesystem"
    assert filesystem["auth_methods"] == ["none"]
    assert filesystem["supports_incremental_sync"] is True
    assert filesystem["supports_delete_detection"] is True

    health = client.get("/connectors/health", headers=headers)
    assert health.status_code == 200
    health_body = health.json()
    snapshot = next(item for item in health_body["items"] if item["connector_id"] == "filesystem")
    assert snapshot["status"] == "healthy"

    empty = client.get("/connectors/filesystem/folders", headers=headers)
    assert empty.status_code == 200
    assert empty.json() == {"items": [], "count": 0}

    created = _add_folder(client, tmp_path, display_name="  Vault  ")
    folder_id = str(created["id"])
    assert created["workspace_id"] == workspace_id
    assert created["display_name"] == "Vault"
    assert created["sync_status"] == "idle"
    assert created["imported_document_count"] == 0
    assert Path(str(created["root_path"])).resolve() == tmp_path.resolve()

    listed = client.get("/connectors/filesystem/folders", headers=headers)
    assert listed.status_code == 200
    listed_body = listed.json()
    assert listed_body["count"] == 1
    assert listed_body["items"][0]["id"] == folder_id

    with Session(engine) as session:
        repository = SqlAlchemyFilesystemFolderRepository(session)
        persisted = repository.get_by_id(folder_id, workspace_id=WorkspaceId(workspace_id))
        assert persisted is not None
        assert persisted.display_name == "Vault"
        assert persisted.sync_status == "idle"
        assert persisted.workspace_id.value == workspace_id
        assert Path(persisted.root_path).resolve() == tmp_path.resolve()

    synced = client.post(
        f"/connectors/filesystem/folders/{folder_id}/sync",
        headers=headers,
        json={},
    )
    assert synced.status_code == 200
    sync_body = synced.json()
    assert sync_body["success"] is True
    assert sync_body["sync_mode"] == "initial"
    assert sync_body["imported_count"] == 1
    assert sync_body["folder"]["id"] == folder_id
    assert sync_body["folder"]["sync_status"] == "healthy"
    assert sync_body["folder"]["imported_document_count"] == 1
    assert sync_body["folder"]["last_synchronized_at"] is not None
    assert sync_body["error_code"] is None

    documents = client.get("/documents", headers=headers)
    assert documents.status_code == 200
    imported = documents.json()["items"]
    assert len(imported) == 1
    assert imported[0]["name"] == "notes.md"
    assert imported[0]["source_type"] == "connector"

    with Session(engine) as session:
        repository = SqlAlchemyFilesystemFolderRepository(session)
        after_sync = repository.get_by_id(folder_id, workspace_id=WorkspaceId(workspace_id))
        assert after_sync is not None
        assert after_sync.sync_status == "healthy"
        assert after_sync.imported_document_count == 1
        assert after_sync.sync_cursor is not None
        assert after_sync.last_synchronized_at is not None
        assert after_sync.last_error is None

    removed = client.delete(
        f"/connectors/filesystem/folders/{folder_id}",
        headers=headers,
    )
    assert removed.status_code == 204
    remaining = client.get("/connectors/filesystem/folders", headers=headers)
    assert remaining.status_code == 200
    assert remaining.json()["count"] == 0

    with Session(engine) as session:
        repository = SqlAlchemyFilesystemFolderRepository(session)
        assert repository.get_by_id(folder_id, workspace_id=WorkspaceId(workspace_id)) is None


def test_connectors_reject_invalid_input_unknown_and_duplicate_folder(
    connectors_client: tuple[TestClient, Engine],
    tmp_path: Path,
) -> None:
    client, _engine = connectors_client
    headers = _headers()
    (tmp_path / "notes.md").write_text("ok", encoding="utf-8")

    blank = client.post(
        "/connectors/filesystem/folders",
        headers=headers,
        json={"root_path": ""},
    )
    assert blank.status_code == 422

    missing_path = client.post(
        "/connectors/filesystem/folders",
        headers=headers,
        json={"root_path": str(tmp_path / "does-not-exist")},
    )
    assert missing_path.status_code == 400
    assert "does not exist" in missing_path.json()["detail"]

    created = _add_folder(client, tmp_path)
    folder_id = str(created["id"])

    duplicate = client.post(
        "/connectors/filesystem/folders",
        headers=headers,
        json={"root_path": str(tmp_path)},
    )
    assert duplicate.status_code == 400
    assert "already connected" in duplicate.json()["detail"]

    unknown_sync = client.post(
        f"/connectors/filesystem/folders/{MISSING_FOLDER_ID}/sync",
        headers=headers,
        json={},
    )
    assert unknown_sync.status_code == 404

    unknown_delete = client.delete(
        f"/connectors/filesystem/folders/{MISSING_FOLDER_ID}",
        headers=headers,
    )
    assert unknown_delete.status_code == 404

    invalid_mode = client.post(
        f"/connectors/filesystem/folders/{folder_id}/sync",
        headers=headers,
        json={"sync_mode": "full"},
    )
    assert invalid_mode.status_code == 422


def test_filesystem_folders_are_isolated_by_workspace(
    connectors_client: tuple[TestClient, Engine],
    tmp_path: Path,
) -> None:
    client, engine = connectors_client
    default_headers = _headers()
    folder_a = tmp_path / "workspace-a"
    folder_b = tmp_path / "workspace-b"
    folder_a.mkdir()
    folder_b.mkdir()
    (folder_a / "a.md").write_text("a", encoding="utf-8")
    (folder_b / "b.md").write_text("b", encoding="utf-8")

    other_workspace = client.post("/workspaces", json={"name": "Other"})
    assert other_workspace.status_code == 201
    other_id = other_workspace.json()["id"]
    other_headers = _headers(other_id)

    in_default = _add_folder(client, folder_a, display_name="Default folder")
    default_folder_id = str(in_default["id"])

    in_other = _add_folder(
        client,
        folder_b,
        workspace_id=other_id,
        display_name="Other folder",
    )
    other_folder_id = str(in_other["id"])

    default_list = client.get("/connectors/filesystem/folders", headers=default_headers).json()
    other_list = client.get("/connectors/filesystem/folders", headers=other_headers).json()
    assert {item["id"] for item in default_list["items"]} == {default_folder_id}
    assert {item["id"] for item in other_list["items"]} == {other_folder_id}

    assert (
        client.post(
            f"/connectors/filesystem/folders/{default_folder_id}/sync",
            headers=other_headers,
            json={},
        ).status_code
        == 404
    )
    assert (
        client.delete(
            f"/connectors/filesystem/folders/{default_folder_id}",
            headers=other_headers,
        ).status_code
        == 404
    )

    still_default = client.get("/connectors/filesystem/folders", headers=default_headers).json()
    assert {item["id"] for item in still_default["items"]} == {default_folder_id}

    synced = client.post(
        f"/connectors/filesystem/folders/{default_folder_id}/sync",
        headers=default_headers,
        json={},
    )
    assert synced.status_code == 200
    assert synced.json()["success"] is True

    with Session(engine) as session:
        repository = SqlAlchemyFilesystemFolderRepository(session)
        assert repository.get_by_id(default_folder_id, workspace_id=WorkspaceId(other_id)) is None
        owned = repository.get_by_id(
            default_folder_id,
            workspace_id=DEFAULT_WORKSPACE_ID,
        )
        assert owned is not None
        assert owned.display_name == "Default folder"
        assert owned.sync_status == "healthy"
        other_owned = repository.get_by_id(
            other_folder_id,
            workspace_id=WorkspaceId(other_id),
        )
        assert other_owned is not None
        assert other_owned.workspace_id.value == other_id
        assert other_owned.display_name == "Other folder"
