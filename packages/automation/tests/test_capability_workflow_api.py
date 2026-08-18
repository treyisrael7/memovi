"""HTTP + SQLAlchemy coverage for shipped capability and workflow APIs."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

import pytest
from api.app import create_app
from api.capability_framework import configure_capability_execution
from api.database import database_session as api_database_session
from api.document_processing import configure_document_processing
from auth.api.dependencies import get_database_session as get_auth_database_session
from auth.infrastructure.persistence import Base as AuthBase
from documents.infrastructure.queue import NoOpProcessingJobQueue
from documents.infrastructure.storage import InMemoryObjectStorage
from fastapi.testclient import TestClient
from memovi_automation.infrastructure.persistence import Base as AutomationBase
from memovi_automation.infrastructure.persistence.models import CapabilityExecutionRecord
from memovi_intelligence.api.dependencies import (
    get_database_session as get_intelligence_database_session,
)
from memovi_intelligence.infrastructure.persistence import Base as IntelligenceBase
from memovi_shared import DEFAULT_WORKSPACE_ID
from memovi_workspace.api.dependencies import get_database_session as get_workspace_database_session
from memovi_workspace.infrastructure.persistence import Base as WorkspaceBase
from memovi_workspace.infrastructure.persistence.models import WorkspaceRecord
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

WORKSPACE_HEADER = "X-Memovi-Workspace-Id"
KNOWN_ENTRY = "notes.txt"


def _headers(workspace_id: str = DEFAULT_WORKSPACE_ID.value) -> dict[str, str]:
    return {WORKSPACE_HEADER: workspace_id}


@pytest.fixture
def capability_workflow_client(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[tuple[TestClient, Engine, Path]]:
    root = tmp_path.resolve()
    (root / KNOWN_ENTRY).write_text("hello", encoding="utf-8")
    monkeypatch.setenv("MEMOVI_FILESYSTEM_ROOTS", str(root))

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    AuthBase.metadata.create_all(engine)
    WorkspaceBase.metadata.create_all(engine)
    AutomationBase.metadata.create_all(engine)
    IntelligenceBase.metadata.create_all(engine)
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
    configure_capability_execution(app)
    configure_document_processing(
        app,
        session_factory=session_factory,
        queue=NoOpProcessingJobQueue(),
        object_storage=InMemoryObjectStorage(),
    )
    app.dependency_overrides[api_database_session] = database_session
    app.dependency_overrides[get_auth_database_session] = database_session
    app.dependency_overrides[get_workspace_database_session] = database_session
    app.dependency_overrides[get_intelligence_database_session] = database_session

    client = TestClient(app, base_url="https://testserver")
    try:
        register_response = client.post(
            "/auth/register",
            json={"email": "capability-workflow@example.com", "password": "password123"},
        )
        assert register_response.status_code == 201
        yield client, engine, root
    finally:
        client.close()
        engine.dispose()


def _submit_list_directory(
    client: TestClient,
    root: Path,
    *,
    workspace_id: str = DEFAULT_WORKSPACE_ID.value,
    conversation_id: str | None = None,
) -> dict[str, object]:
    body: dict[str, object] = {
        "capability_id": "filesystem",
        "arguments": {"operation": "list_directory", "path": str(root)},
    }
    if conversation_id is not None:
        body["conversation_id"] = conversation_id
    response = client.post(
        "/capabilities/executions",
        headers=_headers(workspace_id),
        json=body,
    )
    assert response.status_code == 202
    return response.json()


def test_capability_http_ask_approve_filesystem_list(
    capability_workflow_client: tuple[TestClient, Engine, Path],
) -> None:
    client, engine, root = capability_workflow_client
    headers = _headers()

    anonymous = TestClient(client.app, base_url="https://testserver")
    unauthenticated = anonymous.get("/capabilities", headers=headers)
    assert unauthenticated.status_code == 401

    listed = client.get("/capabilities", headers=headers)
    assert listed.status_code == 200
    payload = listed.json()
    filesystem = next(item for item in payload["items"] if item["id"] == "filesystem")
    assert filesystem["permission_mode"] == "ask_every_time"

    created = client.post("/conversations", headers=headers)
    assert created.status_code == 201
    conversation_id = created.json()["conversation_id"]

    submitted = _submit_list_directory(client, root, conversation_id=conversation_id)
    execution_id = submitted["execution_id"]
    assert submitted["status"] == "pending_approval"
    assert submitted["capability_id"] == "filesystem"
    assert submitted["conversation_id"] == conversation_id
    assert submitted["metadata"].get("awaiting_approval") is True

    pending = client.get(
        "/capabilities/executions",
        headers=headers,
        params={"status": "pending_approval"},
    )
    assert pending.status_code == 200
    pending_ids = {item["execution_id"] for item in pending.json()["items"]}
    assert execution_id in pending_ids

    audit = client.get("/capabilities/executions/audit", headers=headers, params={"limit": 100})
    assert audit.status_code == 200
    assert any(item["execution_id"] == execution_id for item in audit.json()["items"])

    conversation_executions = client.get(
        f"/conversations/{conversation_id}/capability-executions",
        headers=headers,
    )
    assert conversation_executions.status_code == 200
    conversation_ids = {item["execution_id"] for item in conversation_executions.json()["items"]}
    assert execution_id in conversation_ids

    approved = client.post(
        f"/capabilities/executions/{execution_id}/approve",
        headers=headers,
    )
    assert approved.status_code == 200
    result = approved.json()
    assert result["status"] == "completed"
    assert result["output"]["operation"] == "list_directory"
    assert KNOWN_ENTRY in result["output"]["entries"]

    remaining = client.get(
        "/capabilities/executions",
        headers=headers,
        params={"status": "pending_approval"},
    )
    remaining_ids = {item["execution_id"] for item in remaining.json()["items"]}
    assert execution_id not in remaining_ids

    with Session(engine) as session:
        record = session.get(CapabilityExecutionRecord, execution_id)
        assert record is not None
        assert record.status == "completed"
        assert record.workspace_id == DEFAULT_WORKSPACE_ID.value
        assert record.conversation_id == conversation_id


def test_workflow_http_list_directory_resume_after_approve(
    capability_workflow_client: tuple[TestClient, Engine, Path],
) -> None:
    client, _engine, root = capability_workflow_client
    headers = _headers()

    library = client.get("/workflows", headers=headers)
    assert library.status_code == 200
    workflow_ids = {item["workflow_id"] for item in library.json()["items"]}
    assert "list-directory" in workflow_ids

    executed = client.post(
        "/workflows/list-directory/execute",
        headers=headers,
        json={"variables": {"source_folder": str(root)}},
    )
    assert executed.status_code == 200
    paused = executed.json()
    instance_id = paused["instance_id"]
    assert paused["status"] == "awaiting_approval"
    pending_step = next(
        step
        for step in paused["step_results"]
        if step["status"] == "pending_approval" and step["execution_id"]
    )
    execution_id = pending_step["execution_id"]

    approved = client.post(
        f"/capabilities/executions/{execution_id}/approve",
        headers=headers,
    )
    assert approved.status_code == 200
    assert approved.json()["status"] == "completed"

    history_result = client.get(f"/workflows/history/{instance_id}", headers=headers)
    assert history_result.status_code == 200
    completed = history_result.json()
    assert completed["instance_id"] == instance_id
    assert completed["status"] == "completed"
    assert KNOWN_ENTRY in completed["outputs"]["entries"]

    history = client.get("/workflows/history", headers=headers, params={"limit": 50})
    assert history.status_code == 200
    history_ids = {item["instance_id"] for item in history.json()["items"]}
    assert instance_id in history_ids
    matching = next(item for item in history.json()["items"] if item["instance_id"] == instance_id)
    assert matching["status"] == "completed"
    assert matching["workspace_id"] == DEFAULT_WORKSPACE_ID.value


def test_capability_http_cancel_denies_pending_execution(
    capability_workflow_client: tuple[TestClient, Engine, Path],
) -> None:
    client, _engine, root = capability_workflow_client
    headers = _headers()

    submitted = _submit_list_directory(client, root)
    execution_id = submitted["execution_id"]
    assert submitted["status"] == "pending_approval"

    cancelled = client.post(
        f"/capabilities/executions/{execution_id}/cancel",
        headers=headers,
    )
    assert cancelled.status_code == 200
    payload = cancelled.json()
    assert payload["status"] == "cancelled"
    assert payload["error"]["code"] == "cancelled"

    pending = client.get(
        "/capabilities/executions",
        headers=headers,
        params={"status": "pending_approval"},
    )
    pending_ids = {item["execution_id"] for item in pending.json()["items"]}
    assert execution_id not in pending_ids


def test_capability_executions_are_isolated_by_workspace(
    capability_workflow_client: tuple[TestClient, Engine, Path],
) -> None:
    client, _engine, root = capability_workflow_client
    workspace_a = DEFAULT_WORKSPACE_ID.value
    headers_a = _headers(workspace_a)

    other = client.post("/workspaces", json={"name": "Other"})
    assert other.status_code == 201
    workspace_b = other.json()["id"]
    headers_b = _headers(workspace_b)

    submitted = _submit_list_directory(client, root, workspace_id=workspace_a)
    execution_id = submitted["execution_id"]
    assert submitted["status"] == "pending_approval"
    assert submitted["workspace_id"] == workspace_a

    listed_b = client.get(
        "/capabilities/executions",
        headers=headers_b,
        params={"status": "pending_approval"},
    )
    assert listed_b.status_code == 200
    listed_ids = {item["execution_id"] for item in listed_b.json()["items"]}
    assert execution_id not in listed_ids

    approve_b = client.post(
        f"/capabilities/executions/{execution_id}/approve",
        headers=headers_b,
    )
    assert approve_b.status_code == 404

    listed_a = client.get(
        "/capabilities/executions",
        headers=headers_a,
        params={"status": "pending_approval"},
    )
    listed_a_ids = {item["execution_id"] for item in listed_a.json()["items"]}
    assert execution_id in listed_a_ids
