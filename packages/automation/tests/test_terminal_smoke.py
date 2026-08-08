"""Smoke tests for the production Terminal Capability.

Checklist:
1. Register the Terminal Capability
2. Execute a known command through the Capability Registry
3. Capture structured stdout / exit code
4. Reject empty commands and invalid working directories
5. Execute through the Capability Execution Engine (no bypass)
"""

import sys
from pathlib import Path

import pytest
from memovi_automation import (
    TERMINAL_EXECUTE,
    CapabilityContext,
    CapabilityExecutionEngine,
    CapabilityExecutionRequest,
    CapabilityExecutionStatus,
    CapabilityInvoker,
    CapabilityRegistry,
    CapabilityRequest,
    InMemoryExecutionAuditStore,
    InMemoryPermissionPolicyStore,
    PermissionMode,
    TerminalCapabilityConfig,
    register_terminal_capability,
)
from memovi_automation.terminal import CAPABILITY_ID
from memovi_automation.testing import make_auth_context
from memovi_shared import WorkspaceId


@pytest.fixture
def smoke_root(tmp_path: Path) -> Path:
    root = tmp_path / "terminal-smoke"
    root.mkdir()
    return root


def _compose(root: Path) -> tuple[CapabilityRegistry, CapabilityInvoker]:
    registry = CapabilityRegistry()
    register_terminal_capability(
        registry,
        TerminalCapabilityConfig.from_roots([root]),
    )
    return registry, CapabilityInvoker(registry=registry)


def _context() -> CapabilityContext:
    return CapabilityContext.create(
        workspace_id=WorkspaceId.default(),
        granted_permissions=frozenset({TERMINAL_EXECUTE}),
        correlation_id="terminal-smoke",
    )


def test_smoke_register_terminal_capability(smoke_root: Path) -> None:
    registry, _invoker = _compose(smoke_root)

    assert registry.contains("terminal")
    assert "terminal" in registry.ids
    metadata = registry.metadata("terminal")
    assert metadata.id == CAPABILITY_ID
    assert TERMINAL_EXECUTE in metadata.permissions
    assert "terminal.execute" in metadata.permission_names()


def test_smoke_execute_known_command_through_registry(smoke_root: Path) -> None:
    registry, invoker = _compose(smoke_root)
    assert registry.get("terminal").metadata().id == "terminal"

    result = invoker.invoke(
        CapabilityRequest.create(
            capability_id=CAPABILITY_ID,
            arguments={"command": "echo smoke-ok"},
        ),
        _context(),
    )

    assert result.success is True
    assert result.error is None
    assert result.capability_id == "terminal"
    assert result.output is not None
    assert result.output["operation"] == "execute"
    assert result.output["exit_code"] == 0
    assert "smoke-ok" in result.output["stdout"]


def test_smoke_empty_command_and_invalid_cwd_rejected(smoke_root: Path) -> None:
    _registry, invoker = _compose(smoke_root)

    empty = invoker.invoke(
        CapabilityRequest.create(
            capability_id=CAPABILITY_ID,
            arguments={"command": ""},
        ),
        _context(),
    )
    assert empty.success is False
    assert empty.error is not None
    assert empty.error.code == "empty_command"

    bad_cwd = invoker.invoke(
        CapabilityRequest.create(
            capability_id=CAPABILITY_ID,
            arguments={
                "command": "echo x",
                "working_directory": str(smoke_root / "nope"),
            },
        ),
        _context(),
    )
    assert bad_cwd.success is False
    assert bad_cwd.error is not None
    assert bad_cwd.error.code == "invalid_working_directory"


def test_smoke_engine_path_is_required_production_path(smoke_root: Path) -> None:
    registry = CapabilityRegistry()
    register_terminal_capability(
        registry,
        TerminalCapabilityConfig.from_roots([smoke_root]),
    )
    policies = InMemoryPermissionPolicyStore(default_mode=PermissionMode.ALWAYS_ALLOW)
    policies.set("terminal", PermissionMode.ALWAYS_ALLOW, workspace_id=WorkspaceId.default())
    engine = CapabilityExecutionEngine(
        registry=registry,
        invoker=CapabilityInvoker(registry=registry),
        permission_policies=policies,
        audit_store=InMemoryExecutionAuditStore(),
        default_permission_mode=PermissionMode.ALWAYS_ALLOW,
    )

    result = engine.submit(
        CapabilityExecutionRequest.create(
            capability_id="terminal",
            workspace_id=WorkspaceId.default(),
            arguments={"command": "echo via-engine"},
            source="smoke",
        ),
        make_auth_context(),
    )

    assert result.status is CapabilityExecutionStatus.COMPLETED
    assert result.output is not None
    assert "via-engine" in result.output["stdout"]
    audit = engine.list_audit(workspace_id=WorkspaceId.default())
    assert len(audit) >= 2


@pytest.mark.skipif(sys.platform == "win32", reason="uses POSIX pwd")
def test_smoke_working_directory_on_posix(smoke_root: Path) -> None:
    _registry, invoker = _compose(smoke_root)
    result = invoker.invoke(
        CapabilityRequest.create(
            capability_id=CAPABILITY_ID,
            arguments={"command": "pwd", "working_directory": str(smoke_root)},
        ),
        _context(),
    )
    assert result.success is True
    assert str(smoke_root.resolve()) in result.output["stdout"]
