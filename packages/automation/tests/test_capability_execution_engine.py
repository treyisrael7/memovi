from pathlib import Path

from memovi_automation import (
    CapabilityExecutionEngine,
    CapabilityExecutionPolicy,
    CapabilityExecutionRequest,
    CapabilityExecutionStatus,
    CapabilityInvoker,
    CapabilityRegistry,
    FilesystemCapabilityConfig,
    InMemoryExecutionAuditStore,
    InMemoryPermissionPolicyStore,
    PermissionMode,
    register_filesystem_capability,
)
from memovi_shared import WorkspaceId


def _engine(tmp_path: Path, *, mode: PermissionMode) -> CapabilityExecutionEngine:
    registry = CapabilityRegistry()
    register_filesystem_capability(
        registry,
        FilesystemCapabilityConfig.from_roots([tmp_path]),
    )
    policies = InMemoryPermissionPolicyStore(default_mode=mode)
    policies.set("filesystem", mode, workspace_id=WorkspaceId.default())
    return CapabilityExecutionEngine(
        registry=registry,
        invoker=CapabilityInvoker(registry=registry),
        permission_policies=policies,
        audit_store=InMemoryExecutionAuditStore(),
        default_permission_mode=mode,
    )


def test_always_allow_executes_filesystem_capability(tmp_path: Path) -> None:
    target = tmp_path / "note.txt"
    target.write_text("hello capability", encoding="utf-8")
    engine = _engine(tmp_path, mode=PermissionMode.ALWAYS_ALLOW)

    result = engine.submit(
        CapabilityExecutionRequest.create(
            capability_id="filesystem",
            workspace_id=WorkspaceId.default(),
            arguments={
                "operation": "read_file",
                "path": str(target),
            },
            source="test",
        )
    )

    assert result.status is CapabilityExecutionStatus.COMPLETED
    assert result.output is not None
    assert "hello capability" in str(result.output)
    audit = engine.list_audit(workspace_id=WorkspaceId.default())
    assert len(audit) >= 2  # executing + completed


def test_ask_every_time_requires_approval(tmp_path: Path) -> None:
    target = tmp_path / "note.txt"
    target.write_text("needs approval", encoding="utf-8")
    engine = _engine(tmp_path, mode=PermissionMode.ASK_EVERY_TIME)

    pending = engine.submit(
        CapabilityExecutionRequest.create(
            capability_id="filesystem",
            workspace_id=WorkspaceId.default(),
            arguments={"operation": "read_file", "path": str(target)},
        )
    )
    assert pending.status is CapabilityExecutionStatus.PENDING_APPROVAL

    completed = engine.approve(pending.execution_id, workspace_id=WorkspaceId.default())
    assert completed.status is CapabilityExecutionStatus.COMPLETED


def test_deny_policy_blocks_execution(tmp_path: Path) -> None:
    engine = _engine(tmp_path, mode=PermissionMode.DENY)
    result = engine.submit(
        CapabilityExecutionRequest.create(
            capability_id="filesystem",
            workspace_id=WorkspaceId.default(),
            arguments={"operation": "exists", "path": str(tmp_path)},
        )
    )
    assert result.status is CapabilityExecutionStatus.FAILED
    assert result.error is not None
    assert result.error.code == "permission_denied"


def test_request_permission_mode_override(tmp_path: Path) -> None:
    target = tmp_path / "note.txt"
    target.write_text("override", encoding="utf-8")
    engine = _engine(tmp_path, mode=PermissionMode.DENY)

    result = engine.submit(
        CapabilityExecutionRequest.create(
            capability_id="filesystem",
            workspace_id=WorkspaceId.default(),
            arguments={"operation": "read_file", "path": str(target)},
            policy=CapabilityExecutionPolicy(permission_mode=PermissionMode.ALWAYS_ALLOW),
        )
    )
    assert result.status is CapabilityExecutionStatus.COMPLETED


def test_cancel_pending_execution(tmp_path: Path) -> None:
    engine = _engine(tmp_path, mode=PermissionMode.ASK_EVERY_TIME)
    pending = engine.submit(
        CapabilityExecutionRequest.create(
            capability_id="filesystem",
            workspace_id=WorkspaceId.default(),
            arguments={"operation": "exists", "path": str(tmp_path)},
        )
    )
    cancelled = engine.cancel(pending.execution_id, workspace_id=WorkspaceId.default())
    assert cancelled.status is CapabilityExecutionStatus.CANCELLED


def test_audit_redacts_sensitive_arguments(tmp_path: Path) -> None:
    engine = _engine(tmp_path, mode=PermissionMode.ALWAYS_ALLOW)
    engine.submit(
        CapabilityExecutionRequest.create(
            capability_id="filesystem",
            workspace_id=WorkspaceId.default(),
            arguments={
                "operation": "exists",
                "path": str(tmp_path),
                "api_token": "super-secret",
            },
        )
    )
    entries = engine.list_audit(workspace_id=WorkspaceId.default())
    assert any(entry.arguments.get("api_token") == "[REDACTED]" for entry in entries)
