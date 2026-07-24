"""Milestone 22 acceptance checklist for Filesystem write capability."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from memovi_automation import (
    FILESYSTEM_CREATE,
    FILESYSTEM_DELETE,
    FILESYSTEM_MODIFY,
    FILESYSTEM_MOVE,
    FILESYSTEM_READ,
    CapabilityContext,
    CapabilityExecutionEngine,
    CapabilityExecutionPolicy,
    CapabilityExecutionRequest,
    CapabilityInvoker,
    CapabilityRegistry,
    CapabilityRequest,
    FilesystemCapabilityConfig,
    InMemoryExecutionAuditStore,
    InMemoryPermissionPolicyStore,
    PermissionMode,
    register_filesystem_capability,
)
from memovi_automation.filesystem import CAPABILITY_ID, OVERWRITE_REJECTED
from memovi_shared import WorkspaceId

WRITE_OPS_UNDER_TEST = (
    "create_file",
    "create_directory",
    "rename_file",
    "move_file",
    "copy_directory",
    "delete_file",
)


@pytest.fixture
def sandbox(tmp_path: Path) -> Path:
    root = tmp_path / "workspace-root"
    root.mkdir()
    (root / "original.txt").write_text("payload-v1", encoding="utf-8")
    nested = root / "src"
    nested.mkdir()
    (nested / "child.txt").write_text("child-body", encoding="utf-8")
    (nested / "sub").mkdir()
    (nested / "sub" / "deep.txt").write_text("deep-body", encoding="utf-8")
    return root


@pytest.fixture
def engine_stack(sandbox: Path):
    registry = CapabilityRegistry()
    register_filesystem_capability(
        registry,
        FilesystemCapabilityConfig.from_roots(
            [sandbox],
            default_overwrite_policy="reject",
            default_delete_mode="trash",
        ),
    )
    invoker = CapabilityInvoker(registry=registry)
    audit = InMemoryExecutionAuditStore()
    engine = CapabilityExecutionEngine(
        registry=registry,
        invoker=invoker,
        permission_policies=InMemoryPermissionPolicyStore(),
        audit_store=audit,
        default_permission_mode=PermissionMode.ALWAYS_ALLOW,
    )
    return sandbox, invoker, engine, audit


def _context() -> CapabilityContext:
    return CapabilityContext.create(
        workspace_id=WorkspaceId.default(),
        granted_permissions=frozenset(
            {
                FILESYSTEM_READ,
                FILESYSTEM_CREATE,
                FILESYSTEM_MODIFY,
                FILESYSTEM_MOVE,
                FILESYSTEM_DELETE,
            }
        ),
        correlation_id="m22-acceptance",
    )


def _invoke(invoker: CapabilityInvoker, arguments: dict[str, object]):
    return invoker.invoke(
        CapabilityRequest.create(capability_id=CAPABILITY_ID, arguments=arguments),
        _context(),
    )


def _submit(engine: CapabilityExecutionEngine, arguments: dict[str, object]):
    return engine.submit(
        CapabilityExecutionRequest.create(
            capability_id=CAPABILITY_ID,
            workspace_id=WorkspaceId.default(),
            arguments=arguments,
            policy=CapabilityExecutionPolicy(permission_mode=PermissionMode.ALWAYS_ALLOW),
            source="acceptance",
        )
    )


def test_acceptance_1_create_file_and_verify_exists(engine_stack) -> None:
    sandbox, invoker, _engine, _audit = engine_stack

    created = _invoke(
        invoker,
        {
            "operation": "create_file",
            "path": "created.txt",
            "content": "hello-memovi",
        },
    )
    assert created.success is True
    assert (sandbox / "created.txt").is_file()

    exists = _invoke(invoker, {"operation": "exists", "path": "created.txt"})
    assert exists.success is True
    assert exists.output is not None
    assert exists.output["exists"] is True
    assert exists.output["is_file"] is True
    assert (sandbox / "created.txt").read_text(encoding="utf-8") == "hello-memovi"


def test_acceptance_2_create_directory_and_verify_accessible(engine_stack) -> None:
    sandbox, invoker, _engine, _audit = engine_stack

    created = _invoke(
        invoker,
        {"operation": "create_directory", "path": "new-dir"},
    )
    assert created.success is True
    assert (sandbox / "new-dir").is_dir()

    listed = _invoke(invoker, {"operation": "list_directory", "path": "new-dir"})
    assert listed.success is True
    assert listed.output is not None
    assert listed.output["entries"] == []
    assert listed.output["count"] == 0


def test_acceptance_3_rename_file_and_verify_new_path(engine_stack) -> None:
    sandbox, invoker, _engine, _audit = engine_stack

    renamed = _invoke(
        invoker,
        {
            "operation": "rename_file",
            "path": "original.txt",
            "destination": "renamed.txt",
        },
    )
    assert renamed.success is True
    assert renamed.output is not None
    assert renamed.output["destination"].endswith("renamed.txt")
    assert not (sandbox / "original.txt").exists()
    assert (sandbox / "renamed.txt").is_file()
    assert (sandbox / "renamed.txt").read_text(encoding="utf-8") == "payload-v1"


def test_acceptance_4_move_file_contents_unchanged(engine_stack) -> None:
    sandbox, invoker, _engine, _audit = engine_stack
    (sandbox / "inbox").mkdir()
    expected = (sandbox / "src" / "child.txt").read_text(encoding="utf-8")

    moved = _invoke(
        invoker,
        {
            "operation": "move_file",
            "path": "src/child.txt",
            "destination": "inbox/child.txt",
        },
    )
    assert moved.success is True
    assert not (sandbox / "src" / "child.txt").exists()
    assert (sandbox / "inbox" / "child.txt").is_file()
    assert (sandbox / "inbox" / "child.txt").read_text(encoding="utf-8") == expected
    assert expected == "child-body"


def test_acceptance_5_copy_directory_preserves_contents(engine_stack) -> None:
    sandbox, invoker, _engine, _audit = engine_stack

    copied = _invoke(
        invoker,
        {
            "operation": "copy_directory",
            "path": "src",
            "destination": "src-copy",
        },
    )
    assert copied.success is True
    assert (sandbox / "src").is_dir()
    assert (sandbox / "src-copy" / "child.txt").read_text(encoding="utf-8") == "child-body"
    assert (sandbox / "src-copy" / "sub" / "deep.txt").read_text(encoding="utf-8") == "deep-body"

    listing = _invoke(invoker, {"operation": "read_directory", "path": "src-copy"})
    assert listing.success is True
    assert listing.output is not None
    names = {entry["name"] for entry in listing.output["entries"]}
    assert names == {"child.txt", "sub"}


def test_acceptance_6_delete_file_uses_trash_when_supported(engine_stack) -> None:
    sandbox, invoker, _engine, _audit = engine_stack
    (sandbox / "to-trash.txt").write_text("bye", encoding="utf-8")

    with patch(
        "memovi_automation.filesystem.write_operations.move_to_trash",
        return_value={
            "delete_mode": "trash",
            "trash_backend": "acceptance-mock",
            "undo_available": True,
            "undo_message": "Moved to Trash. Restore from Trash if needed.",
        },
    ) as trash:
        deleted = _invoke(
            invoker,
            {
                "operation": "delete_file",
                "path": "to-trash.txt",
                "delete_mode": "trash",
            },
        )
        trash.assert_called_once()

    assert deleted.success is True
    assert deleted.output is not None
    assert deleted.output["metadata"]["delete_mode"] == "trash"
    assert deleted.output["metadata"]["undo_available"] is True
    assert "Trash" in deleted.output["metadata"]["undo_message"]


def test_acceptance_7_overwrite_policy_reject_is_respected(engine_stack) -> None:
    sandbox, invoker, _engine, _audit = engine_stack
    original = (sandbox / "original.txt").read_text(encoding="utf-8")

    rejected = _invoke(
        invoker,
        {
            "operation": "create_file",
            "path": "original.txt",
            "content": "should-not-land",
            "overwrite_policy": "reject",
        },
    )
    assert rejected.success is False
    assert rejected.error is not None
    assert rejected.error.code in {OVERWRITE_REJECTED, "already_exists"}
    assert (sandbox / "original.txt").read_text(encoding="utf-8") == original


def test_acceptance_8_path_traversal_is_rejected(engine_stack, tmp_path: Path) -> None:
    sandbox, invoker, _engine, _audit = engine_stack
    outside = tmp_path / "outside"
    outside.mkdir()
    secret = outside / "secret.txt"
    secret.write_text("classified", encoding="utf-8")

    attack = _invoke(
        invoker,
        {
            "operation": "create_file",
            "path": "../outside/pwned.txt",
            "content": "nope",
        },
    )
    assert attack.success is False
    assert attack.error is not None
    assert attack.error.code == "invalid_path"
    assert not (outside / "pwned.txt").exists()
    assert secret.read_text(encoding="utf-8") == "classified"

    absolute_escape = _invoke(
        invoker,
        {
            "operation": "read_file",
            "path": str(secret),
        },
    )
    assert absolute_escape.success is False
    assert absolute_escape.error is not None
    assert absolute_escape.error.code == "invalid_path"


def test_acceptance_9_every_write_creates_audit_record(engine_stack) -> None:
    sandbox, _invoker, engine, audit = engine_stack
    workspace = WorkspaceId.default()

    operations: list[dict[str, object]] = [
        {
            "operation": "create_file",
            "path": "audit-a.txt",
            "content": "secret-should-redact",
        },
        {"operation": "create_directory", "path": "audit-dir"},
        {
            "operation": "rename_file",
            "path": "audit-a.txt",
            "destination": "audit-b.txt",
        },
        {
            "operation": "move_file",
            "path": "audit-b.txt",
            "destination": "audit-dir/audit-b.txt",
        },
        {
            "operation": "copy_directory",
            "path": "src",
            "destination": "audit-src-copy",
        },
        {
            "operation": "delete_file",
            "path": "audit-dir/audit-b.txt",
            "delete_mode": "permanent",
        },
    ]

    with patch(
        "memovi_automation.filesystem.write_operations.move_to_trash",
        side_effect=AssertionError("trash should not be used in this audit case"),
    ):
        for arguments in operations:
            result = _submit(engine, arguments)
            assert result.status.value == "completed", arguments["operation"]

    entries = audit.list_for_workspace(workspace_id=workspace, limit=100)
    completed_writes = [
        entry
        for entry in entries
        if entry.status.value == "completed"
        and entry.result_summary.get("operation") in WRITE_OPS_UNDER_TEST
    ]
    seen_ops = {entry.result_summary["operation"] for entry in completed_writes}
    assert seen_ops == set(WRITE_OPS_UNDER_TEST)

    for entry in completed_writes:
        assert entry.workspace_id == workspace.value
        assert entry.capability_id == CAPABILITY_ID
        assert entry.result_summary["success"] is True
        assert "target" in entry.result_summary
        if "content" in entry.arguments:
            assert entry.arguments["content"] == "[REDACTED]"

    assert (sandbox / "audit-dir").is_dir()
    assert (sandbox / "audit-src-copy" / "child.txt").exists()
