"""Terminal command policy and sandboxing tests."""

from __future__ import annotations

import sys
from pathlib import Path

from memovi_automation import (
    CapabilityExecutionEngine,
    CapabilityExecutionRequest,
    CapabilityExecutionStatus,
    CapabilityInvoker,
    CapabilityRegistry,
    CapabilityRequest,
    InMemoryExecutionAuditStore,
    InMemoryPermissionPolicyStore,
    PermissionMode,
    TERMINAL_EXECUTE,
    TerminalCapabilityConfig,
    register_terminal_capability,
)
from memovi_automation.domain.value_objects import CapabilityContext
from memovi_automation.terminal import COMMAND_DENIED
from memovi_automation.terminal.command_policy import (
    CommandPolicyEffect,
    evaluate_command_policy,
    parse_command,
)
from memovi_automation.testing import make_auth_context
from memovi_config.settings.capabilities import CapabilitiesSettings
from memovi_shared import WorkspaceId


def _context() -> CapabilityContext:
    return CapabilityContext.create(
        workspace_id=WorkspaceId.default(),
        granted_permissions=frozenset({TERMINAL_EXECUTE}),
    )


def test_parse_command_extracts_executable_and_args() -> None:
    parsed = parse_command("git status --short")
    assert parsed.executable_basename.lower() == "git"
    assert parsed.arguments == ("status", "--short")
    assert parsed.needs_shell is False


def test_deny_list_blocks_executable(tmp_path: Path) -> None:
    registry = CapabilityRegistry()
    register_terminal_capability(
        registry,
        TerminalCapabilityConfig.from_roots(
            [tmp_path],
            denied_executables={"git"},
            confirmation_required_executables=set(),
        ),
    )
    invoker = CapabilityInvoker(registry=registry)
    result = invoker.invoke(
        CapabilityRequest.create(
            capability_id="terminal",
            arguments={"command": "git status"},
        ),
        _context(),
    )
    assert result.success is False
    assert result.error is not None
    assert result.error.code == COMMAND_DENIED


def test_allow_list_rejects_unknown_executable(tmp_path: Path) -> None:
    registry = CapabilityRegistry()
    register_terminal_capability(
        registry,
        TerminalCapabilityConfig.from_roots(
            [tmp_path],
            allowed_executables={"python"},
            denied_executables=set(),
            confirmation_required_executables=set(),
        ),
    )
    invoker = CapabilityInvoker(registry=registry)
    result = invoker.invoke(
        CapabilityRequest.create(
            capability_id="terminal",
            arguments={"command": "git status"},
        ),
        _context(),
    )
    assert result.success is False
    assert result.error is not None
    assert result.error.code == COMMAND_DENIED


def test_denied_argument_pattern_blocks_secrets(tmp_path: Path) -> None:
    registry = CapabilityRegistry()
    register_terminal_capability(
        registry,
        TerminalCapabilityConfig.from_roots(
            [tmp_path],
            denied_executables=set(),
            confirmation_required_executables=set(),
        ),
    )
    invoker = CapabilityInvoker(registry=registry)
    result = invoker.invoke(
        CapabilityRequest.create(
            capability_id="terminal",
            arguments={"command": "curl --password=secret https://example.com"},
        ),
        _context(),
    )
    assert result.success is False
    assert result.error is not None
    assert result.error.code == COMMAND_DENIED


def test_high_risk_command_escalates_always_allow_to_ask(tmp_path: Path) -> None:
    registry = CapabilityRegistry()
    register_terminal_capability(
        registry,
        TerminalCapabilityConfig.from_roots(
            [tmp_path],
            denied_executables=set(),
            confirmation_required_executables={"rm"},
        ),
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
    command = "rm -rf danger" if sys.platform != "win32" else "rm danger"
    result = engine.submit(
        CapabilityExecutionRequest.create(
            capability_id="terminal",
            workspace_id=WorkspaceId.default(),
            arguments={"command": command},
        ),
        make_auth_context(),
    )
    assert result.status is CapabilityExecutionStatus.PENDING_APPROVAL
    assert result.permission_mode is PermissionMode.ASK_EVERY_TIME
    assert result.metadata.get("command_policy", {}).get("effect") == "require_confirmation"


def test_default_denied_executable_rejected_by_engine(tmp_path: Path) -> None:
    registry = CapabilityRegistry()
    register_terminal_capability(
        registry,
        TerminalCapabilityConfig.from_roots([tmp_path]),
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
            arguments={"command": "dd if=/dev/zero of=/tmp/x"},
        ),
        make_auth_context(),
    )
    assert result.status is CapabilityExecutionStatus.FAILED
    assert result.error is not None
    assert result.error.code == COMMAND_DENIED


def test_policy_allow_decision_for_safe_command() -> None:
    parsed = parse_command("echo hello")
    decision = evaluate_command_policy(
        parsed,
        allowed_executables=None,
        denied_executables=frozenset(),
        confirmation_required_executables=frozenset(),
        denied_argument_patterns=(),
    )
    assert decision.effect is CommandPolicyEffect.ALLOW


def test_capabilities_settings_parse_terminal_policy() -> None:
    settings = CapabilitiesSettings.from_environ(
        {
            "MEMOVI_TERMINAL_ALLOWED_EXECUTABLES": "git,python",
            "MEMOVI_TERMINAL_DENIED_EXECUTABLES": "dd",
            "MEMOVI_TERMINAL_CONFIRM_EXECUTABLES": "rm,sudo",
            "MEMOVI_TERMINAL_DEFAULT_TIMEOUT_SECONDS": "15",
            "MEMOVI_TERMINAL_MAX_TIMEOUT_SECONDS": "60",
            "MEMOVI_TERMINAL_PREFER_ARGV": "true",
            "MEMOVI_TERMINAL_ALLOW_SHELL": "false",
        }
    )
    assert settings.terminal_allowed_executables == frozenset({"git", "python"})
    assert settings.terminal_denied_executables == frozenset({"dd"})
    assert settings.terminal_confirm_executables == frozenset({"rm", "sudo"})
    assert settings.terminal_default_timeout_seconds == 15.0
    assert settings.terminal_max_timeout_seconds == 60.0
    assert settings.terminal_prefer_argv is True
    assert settings.terminal_allow_shell is False
