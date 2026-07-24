"""Tests for Filesystem Capability write operations (Milestone 22)."""

from pathlib import Path
from unittest.mock import patch

import pytest
from memovi_automation import (
    FILESYSTEM_CREATE,
    FILESYSTEM_DELETE,
    FILESYSTEM_MODIFY,
    FILESYSTEM_MOVE,
    FILESYSTEM_READ,
    FILESYSTEM_WRITE,
    CapabilityContext,
    CapabilityExecutionEngine,
    CapabilityExecutionPolicy,
    CapabilityExecutionRequest,
    CapabilityInvoker,
    CapabilityRegistry,
    FilesystemCapabilityConfig,
    InMemoryExecutionAuditStore,
    InMemoryPermissionPolicyStore,
    PermissionMode,
    register_filesystem_capability,
)
from memovi_automation.filesystem import (
    ALREADY_EXISTS,
    CAPABILITY_ID,
    OVERWRITE_CONFIRMATION_REQUIRED,
    OVERWRITE_REJECTED,
    PERMISSION_DENIED,
)
from memovi_shared import WorkspaceId


@pytest.fixture
def sandbox(tmp_path: Path) -> Path:
    root = tmp_path / "allowed"
    root.mkdir()
    (root / "notes.txt").write_text("hello", encoding="utf-8")
    docs = root / "docs"
    docs.mkdir()
    (docs / "a.md").write_text("alpha", encoding="utf-8")
    return root


def _stack(root: Path) -> tuple[CapabilityRegistry, CapabilityInvoker]:
    registry = CapabilityRegistry()
    register_filesystem_capability(
        registry,
        FilesystemCapabilityConfig.from_roots([root], max_write_bytes=1024),
    )
    return registry, CapabilityInvoker(registry=registry)


def _all_write_perms() -> frozenset:
    return frozenset(
        {
            FILESYSTEM_READ,
            FILESYSTEM_CREATE,
            FILESYSTEM_MODIFY,
            FILESYSTEM_MOVE,
            FILESYSTEM_DELETE,
        }
    )


def _context(*, granted: frozenset | None = None) -> CapabilityContext:
    return CapabilityContext.create(
        workspace_id=WorkspaceId.default(),
        granted_permissions=granted if granted is not None else _all_write_perms(),
        correlation_id="filesystem-write-test",
    )


def _invoke(
    invoker: CapabilityInvoker,
    *,
    arguments: dict[str, object],
    granted: frozenset | None = None,
):
    from memovi_automation import CapabilityRequest

    return invoker.invoke(
        CapabilityRequest.create(capability_id=CAPABILITY_ID, arguments=arguments),
        _context(granted=granted),
    )


def test_metadata_declares_write_permissions_and_parameters(sandbox: Path) -> None:
    registry, _invoker = _stack(sandbox)
    metadata = registry.metadata(CAPABILITY_ID)
    names = set(metadata.permission_names())
    assert {
        "filesystem.read",
        "filesystem.create",
        "filesystem.modify",
        "filesystem.move",
        "filesystem.delete",
        "filesystem.write",
    } <= names
    assert {parameter.name for parameter in metadata.parameters} >= {
        "operation",
        "path",
        "destination",
        "content",
        "overwrite_policy",
        "delete_mode",
    }


def test_create_replace_append_file(sandbox: Path) -> None:
    _registry, invoker = _stack(sandbox)

    created = _invoke(
        invoker,
        arguments={
            "operation": "create_file",
            "path": "new.txt",
            "content": "fresh",
        },
    )
    assert created.success is True
    assert created.output is not None
    assert created.output["operation"] == "create_file"
    assert created.output["success"] is True
    assert (sandbox / "new.txt").read_text(encoding="utf-8") == "fresh"

    exists = _invoke(
        invoker,
        arguments={
            "operation": "create_file",
            "path": "new.txt",
            "content": "other",
        },
    )
    assert exists.success is False
    assert exists.error is not None
    assert exists.error.code == ALREADY_EXISTS

    ask = _invoke(
        invoker,
        arguments={
            "operation": "create_file",
            "path": "new.txt",
            "content": "other",
            "overwrite_policy": "ask_user",
        },
    )
    assert ask.success is False
    assert ask.error is not None
    assert ask.error.code == OVERWRITE_CONFIRMATION_REQUIRED

    replaced = _invoke(
        invoker,
        arguments={
            "operation": "replace_file_contents",
            "path": "new.txt",
            "content": "replaced",
        },
    )
    assert replaced.success is True
    assert (sandbox / "new.txt").read_text(encoding="utf-8") == "replaced"

    appended = _invoke(
        invoker,
        arguments={
            "operation": "append_to_file",
            "path": "new.txt",
            "content": "!",
        },
    )
    assert appended.success is True
    assert (sandbox / "new.txt").read_text(encoding="utf-8") == "replaced!"


def test_create_directory_copy_move_rename(sandbox: Path) -> None:
    _registry, invoker = _stack(sandbox)

    mkdir = _invoke(
        invoker,
        arguments={"operation": "create_directory", "path": "out"},
    )
    assert mkdir.success is True
    assert (sandbox / "out").is_dir()

    copied = _invoke(
        invoker,
        arguments={
            "operation": "copy_file",
            "path": "notes.txt",
            "destination": "out/notes-copy.txt",
        },
    )
    assert copied.success is True
    assert (sandbox / "out" / "notes-copy.txt").read_text(encoding="utf-8") == "hello"

    renamed = _invoke(
        invoker,
        arguments={
            "operation": "rename_file",
            "path": "out/notes-copy.txt",
            "destination": "out/renamed.txt",
        },
    )
    assert renamed.success is True
    assert not (sandbox / "out" / "notes-copy.txt").exists()
    assert (sandbox / "out" / "renamed.txt").exists()

    moved = _invoke(
        invoker,
        arguments={
            "operation": "move_file",
            "path": "out/renamed.txt",
            "destination": "moved.txt",
        },
    )
    assert moved.success is True
    assert (sandbox / "moved.txt").exists()

    copy_dir = _invoke(
        invoker,
        arguments={
            "operation": "copy_directory",
            "path": "docs",
            "destination": "docs-copy",
        },
    )
    assert copy_dir.success is True
    assert (sandbox / "docs-copy" / "a.md").read_text(encoding="utf-8") == "alpha"


def test_overwrite_reject_and_replace_for_copy(sandbox: Path) -> None:
    _registry, invoker = _stack(sandbox)
    (sandbox / "target.txt").write_text("old", encoding="utf-8")

    rejected = _invoke(
        invoker,
        arguments={
            "operation": "copy_file",
            "path": "notes.txt",
            "destination": "target.txt",
            "overwrite_policy": "reject",
        },
    )
    assert rejected.success is False
    assert rejected.error is not None
    assert rejected.error.code == OVERWRITE_REJECTED
    assert (sandbox / "target.txt").read_text(encoding="utf-8") == "old"

    replaced = _invoke(
        invoker,
        arguments={
            "operation": "copy_file",
            "path": "notes.txt",
            "destination": "target.txt",
            "overwrite_policy": "replace",
        },
    )
    assert replaced.success is True
    assert (sandbox / "target.txt").read_text(encoding="utf-8") == "hello"


def test_delete_permanent_and_trash(sandbox: Path) -> None:
    _registry, invoker = _stack(sandbox)
    (sandbox / "bye.txt").write_text("x", encoding="utf-8")

    permanent = _invoke(
        invoker,
        arguments={
            "operation": "delete_file",
            "path": "bye.txt",
            "delete_mode": "permanent",
        },
    )
    assert permanent.success is True
    assert permanent.output is not None
    assert permanent.output["metadata"]["delete_mode"] == "permanent"
    assert permanent.output["metadata"]["undo_available"] is False
    assert not (sandbox / "bye.txt").exists()

    (sandbox / "trash-me.txt").write_text("y", encoding="utf-8")
    with patch(
        "memovi_automation.filesystem.write_operations.move_to_trash",
        return_value={
            "delete_mode": "trash",
            "trash_backend": "mock",
            "undo_available": True,
            "undo_message": "Moved to Trash.",
        },
    ) as mock_trash:
        trashed = _invoke(
            invoker,
            arguments={
                "operation": "delete_file",
                "path": "trash-me.txt",
                "delete_mode": "trash",
            },
        )
        mock_trash.assert_called_once()
    assert trashed.success is True
    assert trashed.output is not None
    assert trashed.output["metadata"]["undo_available"] is True
    assert "Trash" in trashed.output["metadata"]["undo_message"]


def test_permission_enforcement_for_write_ops(sandbox: Path) -> None:
    _registry, invoker = _stack(sandbox)

    no_create = _invoke(
        invoker,
        arguments={
            "operation": "create_file",
            "path": "x.txt",
            "content": "x",
        },
        granted=frozenset({FILESYSTEM_READ, FILESYSTEM_MODIFY}),
    )
    assert no_create.success is False
    assert no_create.error is not None
    assert no_create.error.code == PERMISSION_DENIED
    assert no_create.error.details["permission"] == "filesystem.create"

    write_umbrella = _invoke(
        invoker,
        arguments={
            "operation": "create_file",
            "path": "via-write.txt",
            "content": "ok",
        },
        granted=frozenset({FILESYSTEM_WRITE}),
    )
    assert write_umbrella.success is True

    no_delete = _invoke(
        invoker,
        arguments={
            "operation": "delete_file",
            "path": "notes.txt",
            "delete_mode": "permanent",
        },
        granted=frozenset({FILESYSTEM_READ, FILESYSTEM_CREATE}),
    )
    assert no_delete.success is False
    assert no_delete.error is not None
    assert no_delete.error.details["permission"] == "filesystem.delete"


def test_write_rejects_path_traversal(sandbox: Path, tmp_path: Path) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    _registry, invoker = _stack(sandbox)

    result = _invoke(
        invoker,
        arguments={
            "operation": "create_file",
            "path": "../outside/evil.txt",
            "content": "nope",
        },
    )
    assert result.success is False
    assert result.error is not None
    assert result.error.code == "invalid_path"
    assert not (outside / "evil.txt").exists()


def test_refuse_modifying_allowed_root(sandbox: Path) -> None:
    _registry, invoker = _stack(sandbox)

    result = _invoke(
        invoker,
        arguments={
            "operation": "delete_directory",
            "path": str(sandbox),
            "delete_mode": "permanent",
        },
    )
    assert result.success is False
    assert result.error is not None
    assert result.error.code == "unsafe_target"


def test_engine_write_audit_redacts_content(sandbox: Path) -> None:
    registry, invoker = _stack(sandbox)
    audit = InMemoryExecutionAuditStore()
    engine = CapabilityExecutionEngine(
        registry=registry,
        invoker=invoker,
        permission_policies=InMemoryPermissionPolicyStore(),
        audit_store=audit,
        default_permission_mode=PermissionMode.ALWAYS_ALLOW,
    )

    result = engine.submit(
        CapabilityExecutionRequest.create(
            capability_id=CAPABILITY_ID,
            workspace_id=WorkspaceId.default(),
            arguments={
                "operation": "create_file",
                "path": "audited.txt",
                "content": "super-secret-body",
            },
            policy=CapabilityExecutionPolicy(permission_mode=PermissionMode.ALWAYS_ALLOW),
            source="test",
        )
    )
    assert result.status.value == "completed"

    entries = engine.list_audit(workspace_id=WorkspaceId.default())
    assert entries
    latest = entries[-1]
    assert latest.arguments["content"] == "[REDACTED]"
    assert latest.result_summary["operation"] == "create_file"
    assert latest.result_summary["target"] == "audited.txt"
    assert latest.result_summary["success"] is True


def test_engine_ask_then_approve_write(sandbox: Path) -> None:
    registry, invoker = _stack(sandbox)
    engine = CapabilityExecutionEngine(
        registry=registry,
        invoker=invoker,
        permission_policies=InMemoryPermissionPolicyStore(),
        audit_store=InMemoryExecutionAuditStore(),
        default_permission_mode=PermissionMode.ASK_EVERY_TIME,
    )
    workspace = WorkspaceId.default()

    pending = engine.submit(
        CapabilityExecutionRequest.create(
            capability_id=CAPABILITY_ID,
            workspace_id=workspace,
            arguments={
                "operation": "create_file",
                "path": "approved.txt",
                "content": "via-engine",
            },
            source="test",
        )
    )
    assert pending.status.value == "pending_approval"
    assert pending.metadata["operation_summary"]["operation"] == "create_file"

    completed = engine.approve(pending.execution_id, workspace_id=workspace)
    assert completed.status.value == "completed"
    assert (sandbox / "approved.txt").read_text(encoding="utf-8") == "via-engine"
