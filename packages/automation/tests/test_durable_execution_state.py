"""Durable capability execution state and approval recovery tests."""

from __future__ import annotations

from pathlib import Path

from memovi_automation import (
    CapabilityExecutionEngine,
    CapabilityExecutionRequest,
    CapabilityExecutionStatus,
    CapabilityInvoker,
    CapabilityRegistry,
    FilesystemCapabilityConfig,
    InMemoryExecutionAuditStore,
    PermissionMode,
    register_filesystem_capability,
)
from memovi_automation.infrastructure.persistence import Base as AutomationBase
from memovi_automation.infrastructure.sqlalchemy_execution_state_store import (
    SqlAlchemyExecutionStateStore,
)
from memovi_automation.infrastructure.sqlalchemy_permission_policy_store import (
    SqlAlchemyPermissionPolicyStore,
)
from memovi_automation.testing import make_auth_context
from memovi_shared import WorkspaceId
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


def _engine(
    tmp_path: Path,
    factory: sessionmaker,
    *,
    mode: PermissionMode,
) -> CapabilityExecutionEngine:
    registry = CapabilityRegistry()
    register_filesystem_capability(
        registry,
        FilesystemCapabilityConfig.from_roots([tmp_path]),
    )
    policies = SqlAlchemyPermissionPolicyStore(factory, default_mode=mode)
    policies.set("filesystem", mode, workspace_id=WorkspaceId.default())
    return CapabilityExecutionEngine(
        registry=registry,
        invoker=CapabilityInvoker(registry=registry),
        permission_policies=policies,
        audit_store=InMemoryExecutionAuditStore(),
        execution_store=SqlAlchemyExecutionStateStore(factory),
        default_permission_mode=mode,
    )


def test_pending_approval_survives_engine_reload(tmp_path: Path) -> None:
    engine_db = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    AutomationBase.metadata.create_all(engine_db)
    factory = sessionmaker(bind=engine_db, expire_on_commit=False)

    first = _engine(tmp_path, factory, mode=PermissionMode.ASK_EVERY_TIME)
    target = tmp_path / "notes.txt"
    target.write_text("hello", encoding="utf-8")
    pending = first.submit(
        CapabilityExecutionRequest.create(
            capability_id="filesystem",
            workspace_id=WorkspaceId.default(),
            arguments={"operation": "read_file", "path": str(target)},
        ),
        make_auth_context(),
    )
    assert pending.status is CapabilityExecutionStatus.PENDING_APPROVAL

    # New engine process with the same durable store.
    second = _engine(tmp_path, factory, mode=PermissionMode.ASK_EVERY_TIME)
    listed = second.list_executions(
        workspace_id=WorkspaceId.default(),
        status=CapabilityExecutionStatus.PENDING_APPROVAL,
    )
    assert len(listed) == 1
    assert listed[0].execution_id == pending.execution_id

    approved = second.approve(
        pending.execution_id,
        workspace_id=WorkspaceId.default(),
        context=make_auth_context(),
    )
    assert approved.status is CapabilityExecutionStatus.COMPLETED
    assert "hello" in str(approved.output)
    engine_db.dispose()


def test_completed_history_survives_reload(tmp_path: Path) -> None:
    engine_db = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    AutomationBase.metadata.create_all(engine_db)
    factory = sessionmaker(bind=engine_db, expire_on_commit=False)

    first = _engine(tmp_path, factory, mode=PermissionMode.ALWAYS_ALLOW)
    target = tmp_path / "notes.txt"
    target.write_text("persist-me", encoding="utf-8")
    result = first.submit(
        CapabilityExecutionRequest.create(
            capability_id="filesystem",
            workspace_id=WorkspaceId.default(),
            arguments={"operation": "read_file", "path": str(target)},
        ),
        make_auth_context(),
    )
    assert result.status is CapabilityExecutionStatus.COMPLETED

    second = _engine(tmp_path, factory, mode=PermissionMode.ALWAYS_ALLOW)
    loaded = second.get(result.execution_id, workspace_id=WorkspaceId.default())
    assert loaded.status is CapabilityExecutionStatus.COMPLETED
    assert "persist-me" in str(loaded.output)
    engine_db.dispose()


def test_interrupted_executing_marked_failed_on_recovery(tmp_path: Path) -> None:
    engine_db = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    AutomationBase.metadata.create_all(engine_db)
    factory = sessionmaker(bind=engine_db, expire_on_commit=False)
    store = SqlAlchemyExecutionStateStore(factory)

    first = _engine(tmp_path, factory, mode=PermissionMode.ALWAYS_ALLOW)
    # Simulate a crash mid-execution by writing an executing row directly via store.
    from datetime import UTC, datetime

    from memovi_automation.domain.value_objects.capability_execution_result import (
        CapabilityExecutionResult,
    )

    executing = CapabilityExecutionResult(
        execution_id="exec-interrupted",
        capability_id="filesystem",
        workspace_id=WorkspaceId.default().value,
        status=CapabilityExecutionStatus.EXECUTING,
        permission_mode=PermissionMode.ALWAYS_ALLOW,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        metadata={"source": "test"},
    )
    store.save_result(executing)

    recovered = first.recover_interrupted_executions()
    assert len(recovered) == 1
    assert recovered[0].status is CapabilityExecutionStatus.FAILED
    assert recovered[0].error is not None
    assert recovered[0].error.code == "interrupted_by_restart"

    loaded = first.get("exec-interrupted", workspace_id=WorkspaceId.default())
    assert loaded.status is CapabilityExecutionStatus.FAILED
    engine_db.dispose()
