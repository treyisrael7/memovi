"""Durable workflow library and history persistence tests."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from memovi_automation import (
    CapabilityExecutionEngine,
    CapabilityInvoker,
    CapabilityPlanner,
    CapabilityRegistry,
    FilesystemCapabilityConfig,
    InMemoryExecutionAuditStore,
    PermissionMode,
    PlanExecutionService,
    WorkflowDefinition,
    WorkflowEngine,
    WorkflowStep,
    WorkflowValidator,
    WorkflowVariable,
    register_filesystem_capability,
)
from memovi_automation.infrastructure.persistence import Base as AutomationBase
from memovi_automation.infrastructure.sqlalchemy_permission_policy_store import (
    SqlAlchemyPermissionPolicyStore,
)
from memovi_automation.infrastructure.sqlalchemy_workflow_history_store import (
    SqlAlchemyWorkflowHistoryStore,
)
from memovi_automation.infrastructure.sqlalchemy_workflow_library import (
    SqlAlchemyWorkflowLibrary,
)
from memovi_automation.testing import make_auth_context
from memovi_observability.metrics import get_metrics_recorder
from memovi_shared import WorkspaceId
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


def _session_factory():
    engine_db = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    AutomationBase.metadata.create_all(engine_db)
    factory = sessionmaker(bind=engine_db, expire_on_commit=False)
    return engine_db, factory


def _workflow_engine(tmp_path: Path, factory: sessionmaker) -> WorkflowEngine:
    registry = CapabilityRegistry()
    register_filesystem_capability(
        registry,
        FilesystemCapabilityConfig.from_roots([tmp_path]),
    )
    policies = SqlAlchemyPermissionPolicyStore(
        factory,
        default_mode=PermissionMode.ALWAYS_ALLOW,
    )
    policies.set("filesystem", PermissionMode.ALWAYS_ALLOW, workspace_id=WorkspaceId.default())
    capability_engine = CapabilityExecutionEngine(
        registry=registry,
        invoker=CapabilityInvoker(registry=registry),
        permission_policies=policies,
        audit_store=InMemoryExecutionAuditStore(),
        default_permission_mode=PermissionMode.ALWAYS_ALLOW,
    )
    planner = CapabilityPlanner(registry=registry)
    return WorkflowEngine(
        library=SqlAlchemyWorkflowLibrary(factory),
        planner=planner,
        plan_execution=PlanExecutionService(engine=capability_engine, planner=planner),
        history=SqlAlchemyWorkflowHistoryStore(factory),
        validator=WorkflowValidator(registry=registry),
    )


def test_workflow_definitions_survive_reload(tmp_path: Path) -> None:
    engine_db, factory = _session_factory()
    first = SqlAlchemyWorkflowLibrary(factory)
    assert any(item.workflow_id == "list-directory" for item in first.list())

    custom = WorkflowDefinition(
        workflow_id="custom-list",
        name="Custom List",
        description="Workspace custom workflow",
        workspace_id=WorkspaceId.default().value,
        variables=(WorkflowVariable(name="source_folder", type="path"),),
        steps=(
            WorkflowStep(
                step_id="list",
                capability_id="filesystem",
                operation="list_directory",
                input_mapping={"path": "${source_folder}"},
            ),
        ),
    )
    first.create(custom)
    duplicated = first.duplicate("custom-list", new_workflow_id="custom-list-2")
    assert duplicated.workflow_id == "custom-list-2"
    assert duplicated.version == 1

    second = SqlAlchemyWorkflowLibrary(factory, seed_built_ins=False)
    loaded = second.get("custom-list")
    assert loaded.name == "Custom List"
    assert loaded.version == 1
    assert second.get("custom-list-2").name.startswith("Copy of")

    updated = second.update(
        loaded.with_updates(description="Updated description", bump_version=True),
    )
    assert updated.version == 2
    assert second.get("custom-list").description == "Updated description"

    second.delete("custom-list-2")
    ids = {item.workflow_id for item in second.list()}
    assert "custom-list-2" not in ids
    assert "list-directory" in ids
    engine_db.dispose()


def test_workflow_history_survives_reload(tmp_path: Path) -> None:
    engine_db, factory = _session_factory()
    (tmp_path / "a.txt").write_text("hello", encoding="utf-8")
    first = _workflow_engine(tmp_path, factory)
    result = first.execute(
        workflow_id="list-directory",
        workspace_id=WorkspaceId.default(),
        auth_context=make_auth_context(),
        variables={"source_folder": str(tmp_path)},
    )
    assert result.status == "completed"

    second = _workflow_engine(tmp_path, factory)
    entries = second.history.list_for_workspace(workspace_id=WorkspaceId.default())
    assert len(entries) == 1
    assert entries[0].instance_id == result.instance_id
    assert entries[0].status == "completed"
    assert entries[0].user_id is not None
    assert "list" in entries[0].executed_steps

    loaded = second.history.get_result(
        result.instance_id,
        workspace_id=WorkspaceId.default(),
    )
    assert loaded is not None
    assert loaded.status == "completed"
    assert loaded.outputs["count"] == 1
    engine_db.dispose()


def test_interrupted_running_workflow_marked_failed_on_recovery(tmp_path: Path) -> None:
    engine_db, factory = _session_factory()
    store = SqlAlchemyWorkflowHistoryStore(factory)
    from memovi_automation.domain.value_objects.workflow import WorkflowExecutionResult

    running = WorkflowExecutionResult(
        instance_id="wf-interrupted",
        workflow_id="list-directory",
        workflow_name="List Directory",
        workspace_id=WorkspaceId.default().value,
        status="running",
        started_at=datetime.now(UTC),
        metadata={"user_id": "user-1"},
    )
    store.store_result(running)

    engine = _workflow_engine(tmp_path, factory)
    recovered = engine.recover_interrupted_workflows()
    assert len(recovered) == 1
    assert recovered[0].status == "failed"
    assert recovered[0].metadata.get("recovered") is True

    # Awaiting approval must not be force-failed (no duplicate resume).
    awaiting = WorkflowExecutionResult(
        instance_id="wf-awaiting",
        workflow_id="list-directory",
        workflow_name="List Directory",
        workspace_id=WorkspaceId.default().value,
        status="awaiting_approval",
        started_at=datetime.now(UTC),
    )
    store.store_result(awaiting)
    again = engine.recover_interrupted_workflows()
    assert again == ()
    kept = store.get_result("wf-awaiting", workspace_id=WorkspaceId.default())
    assert kept is not None
    assert kept.status == "awaiting_approval"
    engine_db.dispose()


def test_workflow_metrics_recorded(tmp_path: Path) -> None:
    engine_db, factory = _session_factory()
    (tmp_path / "a.txt").write_text("x", encoding="utf-8")
    recorder = get_metrics_recorder()
    if hasattr(recorder, "reset"):
        recorder.reset()  # type: ignore[attr-defined]

    engine = _workflow_engine(tmp_path, factory)
    result = engine.execute(
        workflow_id="list-directory",
        workspace_id=WorkspaceId.default(),
        auth_context=make_auth_context(),
        variables={"source_folder": str(tmp_path)},
    )
    assert result.status == "completed"
    assert recorder.counters.get("memovi.workflows.execution.completed", 0) >= 1
    assert recorder.timings.get("memovi.workflows.execution.duration_ms")
    engine_db.dispose()
