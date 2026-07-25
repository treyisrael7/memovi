"""Milestone 23 acceptance checklist for Terminal Capability.

1. Execute pwd / platform equivalent and verify working directory
2. Execute ls / dir and verify directory contents
3. Non-zero exit code → structured reporting
4. Long-running command → cancellation
5. Specified working directory is honored
6. stdout, stderr, exit code, duration returned
7. Denied permissions prevent execution
8. Ask Every Time requires approval
9. Every execution creates an audit entry
"""

from __future__ import annotations

import sys
import threading
import time
from pathlib import Path

import pytest
from memovi_automation import (
    CapabilityExecutionEngine,
    CapabilityExecutionPolicy,
    CapabilityExecutionRequest,
    CapabilityExecutionStatus,
    CapabilityInvoker,
    CapabilityRegistry,
    InMemoryExecutionAuditStore,
    InMemoryPermissionPolicyStore,
    PermissionMode,
    TerminalCapabilityConfig,
    register_terminal_capability,
)
from memovi_shared import WorkspaceId


@pytest.fixture
def sandbox(tmp_path: Path) -> Path:
    root = tmp_path / "terminal-acceptance"
    root.mkdir()
    (root / "alpha.txt").write_text("a", encoding="utf-8")
    (root / "beta.txt").write_text("b", encoding="utf-8")
    nested = root / "nested"
    nested.mkdir()
    (nested / "gamma.txt").write_text("g", encoding="utf-8")
    return root


def _engine(
    root: Path,
    *,
    mode: PermissionMode,
) -> CapabilityExecutionEngine:
    registry = CapabilityRegistry()
    register_terminal_capability(
        registry,
        TerminalCapabilityConfig.from_roots([root]),
    )
    policies = InMemoryPermissionPolicyStore(default_mode=mode)
    policies.set("terminal", mode, workspace_id=WorkspaceId.default())
    return CapabilityExecutionEngine(
        registry=registry,
        invoker=CapabilityInvoker(registry=registry),
        permission_policies=policies,
        audit_store=InMemoryExecutionAuditStore(),
        default_permission_mode=mode,
    )


def _submit(
    engine: CapabilityExecutionEngine,
    arguments: dict[str, object],
    *,
    policy: CapabilityExecutionPolicy | None = None,
    source: str = "acceptance",
):
    return engine.submit(
        CapabilityExecutionRequest.create(
            capability_id="terminal",
            workspace_id=WorkspaceId.default(),
            arguments=arguments,
            policy=policy,
            source=source,
        )
    )


def _pwd_command() -> str:
    return "cd" if sys.platform == "win32" else "pwd"


def _list_command() -> str:
    return "dir /b" if sys.platform == "win32" else "ls -1"


def _fail_command() -> str:
    if sys.platform == "win32":
        return "cmd /c exit 9"
    return "sh -c 'exit 9'"


def _sleep_command(seconds: float) -> str:
    if sys.platform == "win32":
        count = max(4, int(seconds) + 1)
        return f"ping -n {count} 127.0.0.1 >NUL"
    return f"sleep {seconds}"


def _stderr_command() -> str:
    if sys.platform == "win32":
        return "cmd /c \"echo out-ok & echo err-ok 1>&2\""
    return "sh -c 'echo out-ok; echo err-ok 1>&2'"


def test_1_pwd_returns_working_directory(sandbox: Path) -> None:
    engine = _engine(sandbox, mode=PermissionMode.ALWAYS_ALLOW)
    result = _submit(engine, {"command": _pwd_command()})

    assert result.status is CapabilityExecutionStatus.COMPLETED
    assert result.output is not None
    assert Path(result.output["working_directory"]) == sandbox.resolve()
    assert str(sandbox.resolve()) in result.output["stdout"].replace("/", "\\") or str(
        sandbox.resolve()
    ) in result.output["stdout"]


def test_2_list_directory_returns_contents(sandbox: Path) -> None:
    engine = _engine(sandbox, mode=PermissionMode.ALWAYS_ALLOW)
    result = _submit(engine, {"command": _list_command()})

    assert result.status is CapabilityExecutionStatus.COMPLETED
    assert result.output is not None
    stdout = result.output["stdout"]
    assert "alpha.txt" in stdout
    assert "beta.txt" in stdout
    assert "nested" in stdout


def test_3_non_zero_exit_structured_reporting(sandbox: Path) -> None:
    engine = _engine(sandbox, mode=PermissionMode.ALWAYS_ALLOW)
    result = _submit(engine, {"command": _fail_command()})

    # Capability invocation completed; payload reports command failure.
    assert result.status is CapabilityExecutionStatus.COMPLETED
    assert result.output is not None
    assert result.output["exit_code"] == 9
    assert result.output["success"] is False
    assert "exit_code" in result.output
    assert "stdout" in result.output
    assert "stderr" in result.output
    assert "duration_seconds" in result.output


def test_4_long_running_command_cancellation(sandbox: Path) -> None:
    engine = _engine(sandbox, mode=PermissionMode.ALWAYS_ALLOW)
    request = CapabilityExecutionRequest.create(
        capability_id="terminal",
        workspace_id=WorkspaceId.default(),
        arguments={"command": _sleep_command(30), "timeout_seconds": 25},
        policy=CapabilityExecutionPolicy(timeout_seconds=60.0, cancellable=True),
        source="acceptance",
    )
    holder: dict[str, object] = {}

    def _run() -> None:
        holder["result"] = engine.submit(request)

    worker = threading.Thread(target=_run, daemon=True)
    worker.start()

    cancelled = None
    deadline = time.time() + 10
    while time.time() < deadline:
        try:
            current = engine.get(request.id, workspace_id=WorkspaceId.default())
        except Exception:
            time.sleep(0.05)
            continue
        if current.status is CapabilityExecutionStatus.EXECUTING:
            cancelled = engine.cancel(request.id, workspace_id=WorkspaceId.default())
            break
        if current.status in {
            CapabilityExecutionStatus.COMPLETED,
            CapabilityExecutionStatus.FAILED,
            CapabilityExecutionStatus.CANCELLED,
        }:
            cancelled = current
            break
        time.sleep(0.05)

    worker.join(timeout=15)
    assert cancelled is not None
    assert cancelled.status is CapabilityExecutionStatus.CANCELLED

    final = holder.get("result")
    assert final is not None
    assert final.status in {
        CapabilityExecutionStatus.CANCELLED,
        CapabilityExecutionStatus.FAILED,
    }
    if final.status is CapabilityExecutionStatus.FAILED:
        assert final.error is not None
        assert final.error.code in {"cancelled", "timeout"}


def test_5_specified_working_directory(sandbox: Path) -> None:
    engine = _engine(sandbox, mode=PermissionMode.ALWAYS_ALLOW)
    nested = sandbox / "nested"
    result = _submit(
        engine,
        {
            "command": _pwd_command(),
            "working_directory": str(nested),
        },
    )

    assert result.status is CapabilityExecutionStatus.COMPLETED
    assert result.output is not None
    assert Path(result.output["working_directory"]) == nested.resolve()
    assert str(nested.resolve()) in result.output["stdout"].replace("/", "\\") or str(
        nested.resolve()
    ) in result.output["stdout"]


def test_6_stdout_stderr_exit_code_duration(sandbox: Path) -> None:
    engine = _engine(sandbox, mode=PermissionMode.ALWAYS_ALLOW)
    result = _submit(engine, {"command": _stderr_command()})

    assert result.status is CapabilityExecutionStatus.COMPLETED
    assert result.output is not None
    assert "out-ok" in result.output["stdout"]
    assert "err-ok" in result.output["stderr"]
    assert result.output["exit_code"] == 0
    assert isinstance(result.output["duration_seconds"], float)
    assert result.output["duration_seconds"] >= 0


def test_7_denied_permissions_prevent_execution(sandbox: Path) -> None:
    engine = _engine(sandbox, mode=PermissionMode.DENY)
    result = _submit(engine, {"command": "echo should-not-run"})

    assert result.status is CapabilityExecutionStatus.FAILED
    assert result.error is not None
    assert result.error.code == "permission_denied"
    assert result.output is None


def test_8_ask_every_time_requires_approval(sandbox: Path) -> None:
    engine = _engine(sandbox, mode=PermissionMode.ASK_EVERY_TIME)
    pending = _submit(engine, {"command": "echo needs-approval"})

    assert pending.status is CapabilityExecutionStatus.PENDING_APPROVAL
    assert pending.output is None

    approved = engine.approve(pending.execution_id, workspace_id=WorkspaceId.default())
    assert approved.status is CapabilityExecutionStatus.COMPLETED
    assert approved.output is not None
    assert "needs-approval" in approved.output["stdout"]


def test_9_every_execution_creates_audit_entry(sandbox: Path) -> None:
    engine = _engine(sandbox, mode=PermissionMode.ALWAYS_ALLOW)
    result = _submit(engine, {"command": "echo audited"})

    assert result.status is CapabilityExecutionStatus.COMPLETED
    audit = engine.list_audit(workspace_id=WorkspaceId.default())
    assert len(audit) >= 2  # executing + completed
    statuses = {entry.status for entry in audit}
    assert CapabilityExecutionStatus.EXECUTING in statuses
    assert CapabilityExecutionStatus.COMPLETED in statuses
    completed = [entry for entry in audit if entry.status is CapabilityExecutionStatus.COMPLETED]
    assert completed
    entry = completed[-1]
    assert entry.capability_id == "terminal"
    assert entry.workspace_id == str(WorkspaceId.default())
    assert entry.arguments.get("command") == "echo audited"
    assert entry.result_summary.get("exit_code") == 0
    assert entry.duration >= 0
    assert entry.timestamp is not None
