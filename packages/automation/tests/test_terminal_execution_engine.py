import sys
import threading
import time
from pathlib import Path

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


def _engine(tmp_path: Path, *, mode: PermissionMode) -> CapabilityExecutionEngine:
    registry = CapabilityRegistry()
    register_terminal_capability(
        registry,
        TerminalCapabilityConfig.from_roots([tmp_path]),
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


def _echo(message: str) -> str:
    return f"echo {message}"


def _sleep(seconds: float) -> str:
    if sys.platform == "win32":
        count = max(3, int(seconds) + 1)
        return f"ping -n {count} 127.0.0.1 >NUL"
    return f"sleep {seconds}"


def test_always_allow_executes_terminal_through_engine(tmp_path: Path) -> None:
    engine = _engine(tmp_path, mode=PermissionMode.ALWAYS_ALLOW)

    result = engine.submit(
        CapabilityExecutionRequest.create(
            capability_id="terminal",
            workspace_id=WorkspaceId.default(),
            arguments={"command": _echo("engine-ok")},
            source="test",
        )
    )

    assert result.status is CapabilityExecutionStatus.COMPLETED
    assert result.output is not None
    assert "engine-ok" in str(result.output["stdout"])
    assert result.output["exit_code"] == 0
    audit = engine.list_audit(workspace_id=WorkspaceId.default())
    assert any(entry.status is CapabilityExecutionStatus.COMPLETED for entry in audit)
    completed = [entry for entry in audit if entry.status is CapabilityExecutionStatus.COMPLETED][0]
    assert completed.result_summary.get("exit_code") == 0
    assert completed.arguments.get("command") == "echo engine-ok"
    assert "env" not in completed.arguments or isinstance(completed.arguments.get("env"), dict)


def test_ask_every_time_requires_approval(tmp_path: Path) -> None:
    engine = _engine(tmp_path, mode=PermissionMode.ASK_EVERY_TIME)

    pending = engine.submit(
        CapabilityExecutionRequest.create(
            capability_id="terminal",
            workspace_id=WorkspaceId.default(),
            arguments={"command": _echo("needs-approval")},
        )
    )
    assert pending.status is CapabilityExecutionStatus.PENDING_APPROVAL
    assert pending.metadata["operation_summary"]["command"] == "echo needs-approval"

    completed = engine.approve(pending.execution_id, workspace_id=WorkspaceId.default())
    assert completed.status is CapabilityExecutionStatus.COMPLETED
    assert "needs-approval" in str(completed.output["stdout"])


def test_deny_policy_blocks_terminal(tmp_path: Path) -> None:
    engine = _engine(tmp_path, mode=PermissionMode.DENY)
    result = engine.submit(
        CapabilityExecutionRequest.create(
            capability_id="terminal",
            workspace_id=WorkspaceId.default(),
            arguments={"command": _echo("blocked")},
        )
    )
    assert result.status is CapabilityExecutionStatus.FAILED
    assert result.error is not None
    assert result.error.code == "permission_denied"


def test_sensitive_env_is_redacted_in_audit(tmp_path: Path) -> None:
    engine = _engine(tmp_path, mode=PermissionMode.ALWAYS_ALLOW)
    result = engine.submit(
        CapabilityExecutionRequest.create(
            capability_id="terminal",
            workspace_id=WorkspaceId.default(),
            arguments={
                "command": _echo("redact"),
                "env": {
                    "VISIBLE_FLAG": "ok",
                    "API_TOKEN": "super-secret",
                    "NORMAL_PATH": "C:\\tmp",
                },
            },
        )
    )
    assert result.status is CapabilityExecutionStatus.COMPLETED
    audit = engine.list_audit(workspace_id=WorkspaceId.default())
    completed = [entry for entry in audit if entry.status is CapabilityExecutionStatus.COMPLETED][0]
    env = completed.arguments["env"]
    assert env["VISIBLE_FLAG"] == "ok"
    assert env["API_TOKEN"] == "[REDACTED]"
    assert env["NORMAL_PATH"] == "C:\\tmp"


def test_cancel_pending_terminal_execution(tmp_path: Path) -> None:
    engine = _engine(tmp_path, mode=PermissionMode.ASK_EVERY_TIME)
    pending = engine.submit(
        CapabilityExecutionRequest.create(
            capability_id="terminal",
            workspace_id=WorkspaceId.default(),
            arguments={"command": _echo("never")},
        )
    )
    cancelled = engine.cancel(pending.execution_id, workspace_id=WorkspaceId.default())
    assert cancelled.status is CapabilityExecutionStatus.CANCELLED


def test_cancel_running_terminal_process(tmp_path: Path) -> None:
    engine = _engine(tmp_path, mode=PermissionMode.ALWAYS_ALLOW)
    request = CapabilityExecutionRequest.create(
        capability_id="terminal",
        workspace_id=WorkspaceId.default(),
        arguments={"command": _sleep(30), "timeout_seconds": 25},
        policy=CapabilityExecutionPolicy(timeout_seconds=60.0, cancellable=True),
        source="test",
    )

    holder: dict[str, object] = {}

    def _run() -> None:
        holder["result"] = engine.submit(request)

    worker = threading.Thread(target=_run, daemon=True)
    worker.start()

    deadline = time.time() + 10
    execution_id = request.id
    while time.time() < deadline:
        try:
            current = engine.get(execution_id, workspace_id=WorkspaceId.default())
        except Exception:
            time.sleep(0.05)
            continue
        if current.status is CapabilityExecutionStatus.EXECUTING:
            cancelled = engine.cancel(execution_id, workspace_id=WorkspaceId.default())
            assert cancelled.status is CapabilityExecutionStatus.CANCELLED
            break
        if current.status in {
            CapabilityExecutionStatus.COMPLETED,
            CapabilityExecutionStatus.FAILED,
            CapabilityExecutionStatus.CANCELLED,
        }:
            break
        time.sleep(0.05)

    worker.join(timeout=15)
    final = holder.get("result")
    assert final is not None
    # Engine cancel marks cancelled; invoke path should also surface cancelled.
    assert final.status in {
        CapabilityExecutionStatus.CANCELLED,
        CapabilityExecutionStatus.FAILED,
    }
    if final.status is CapabilityExecutionStatus.FAILED:
        assert final.error is not None
        assert final.error.code in {"cancelled", "timeout"}
