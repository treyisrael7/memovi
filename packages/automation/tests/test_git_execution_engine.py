import subprocess
from pathlib import Path

import pytest
from memovi_automation.testing import make_auth_context
from memovi_automation import (
    CapabilityExecutionEngine,
    CapabilityExecutionRequest,
    CapabilityExecutionStatus,
    CapabilityInvoker,
    CapabilityRegistry,
    GitCapabilityConfig,
    InMemoryExecutionAuditStore,
    InMemoryPermissionPolicyStore,
    PermissionMode,
    register_git_capability,
)
from memovi_shared import WorkspaceId


def _git_available() -> bool:
    try:
        subprocess.run(["git", "--version"], check=True, capture_output=True, text=True)
        return True
    except (OSError, subprocess.CalledProcessError):
        return False


pytestmark = pytest.mark.skipif(not _git_available(), reason="git CLI unavailable")


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    workspace = tmp_path / "ws"
    workspace.mkdir()
    repo_path = workspace / "repo"
    repo_path.mkdir()
    subprocess.run(["git", "init", "-b", "main"], cwd=repo_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "memovi@example.com"],
        cwd=repo_path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Memovi Test"],
        cwd=repo_path,
        check=True,
        capture_output=True,
    )
    (repo_path / "a.txt").write_text("a", encoding="utf-8")
    subprocess.run(["git", "add", "a.txt"], cwd=repo_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "init"],
        cwd=repo_path,
        check=True,
        capture_output=True,
    )
    return repo_path


def _engine(workspace: Path, *, mode: PermissionMode) -> CapabilityExecutionEngine:
    registry = CapabilityRegistry()
    register_git_capability(registry, GitCapabilityConfig.from_roots([workspace]))
    policies = InMemoryPermissionPolicyStore(default_mode=mode)
    policies.set("git", mode, workspace_id=WorkspaceId.default())
    return CapabilityExecutionEngine(
        registry=registry,
        invoker=CapabilityInvoker(registry=registry),
        permission_policies=policies,
        audit_store=InMemoryExecutionAuditStore(),
        default_permission_mode=mode,
    )


def test_always_allow_executes_git_through_engine(repo: Path) -> None:
    engine = _engine(repo.parent, mode=PermissionMode.ALWAYS_ALLOW)
    result = engine.submit(
        CapabilityExecutionRequest.create(
            capability_id="git",
            workspace_id=WorkspaceId.default(),
            arguments={"operation": "status", "repository": str(repo)},
            source="test",
        ), make_auth_context())
    assert result.status is CapabilityExecutionStatus.COMPLETED
    assert result.output is not None
    assert result.output["operation"] == "status"
    assert result.output["branch"] == "main"
    audit = engine.list_audit(workspace_id=WorkspaceId.default())
    assert any(entry.status is CapabilityExecutionStatus.COMPLETED for entry in audit)
    completed = [e for e in audit if e.status is CapabilityExecutionStatus.COMPLETED][-1]
    assert completed.arguments["operation"] == "status"
    assert completed.arguments["repository"] == str(repo)
    assert completed.result_summary.get("repository") == str(repo)


def test_ask_every_time_requires_approval_for_commit(repo: Path) -> None:
    engine = _engine(repo.parent, mode=PermissionMode.ASK_EVERY_TIME)
    pending = engine.submit(
        CapabilityExecutionRequest.create(
            capability_id="git",
            workspace_id=WorkspaceId.default(),
            arguments={
                "operation": "commit",
                "repository": str(repo),
                "message": "empty ok",
                "allow_empty": True,
            },
        ), make_auth_context())
    assert pending.status is CapabilityExecutionStatus.PENDING_APPROVAL
    assert pending.metadata["operation_summary"]["operation"] == "commit"

    completed = engine.approve(pending.execution_id, workspace_id=WorkspaceId.default(), context=make_auth_context())
    assert completed.status is CapabilityExecutionStatus.COMPLETED
    assert completed.output["short_sha"]


def test_deny_blocks_git(repo: Path) -> None:
    engine = _engine(repo.parent, mode=PermissionMode.DENY)
    result = engine.submit(
        CapabilityExecutionRequest.create(
            capability_id="git",
            workspace_id=WorkspaceId.default(),
            arguments={"operation": "status", "repository": str(repo)},
        ), make_auth_context())
    assert result.status is CapabilityExecutionStatus.FAILED
    assert result.error is not None
    assert result.error.code == "permission_denied"
