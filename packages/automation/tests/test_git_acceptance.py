"""Milestone 24 acceptance checklist for Git Capability.

1. Detect a valid Git repository and return repository metadata.
2. Retrieve repository status and verify modified, staged, and untracked files.
3. List all branches and verify the active branch is identified.
4. Create a test branch, switch to it, then switch back.
5. Stage a modified file and verify status updates accordingly.
6. Commit staged changes with a test message and verify history.
7. Retrieve a diff for a modified file and verify structured output.
8. Attempt a Git operation outside a repository → normalized error.
9. Verify operations requiring confirmation pause until approved.
10. Verify every Git operation creates an audit entry.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from memovi_automation import (
    GIT_NETWORK,
    GIT_READ,
    GIT_WRITE,
    CapabilityContext,
    CapabilityExecutionEngine,
    CapabilityExecutionRequest,
    CapabilityExecutionStatus,
    CapabilityInvoker,
    CapabilityRegistry,
    CapabilityRequest,
    GitCapabilityConfig,
    InMemoryExecutionAuditStore,
    InMemoryPermissionPolicyStore,
    PermissionMode,
    register_git_capability,
)
from memovi_automation.testing import make_auth_context
from memovi_shared import WorkspaceId


def _git_available() -> bool:
    try:
        subprocess.run(["git", "--version"], check=True, capture_output=True, text=True)
        return True
    except OSError, subprocess.CalledProcessError:
        return False


pytestmark = pytest.mark.skipif(not _git_available(), reason="git CLI unavailable")


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    workspace = tmp_path / "accept"
    workspace.mkdir()
    path = workspace / "repo"
    path.mkdir()
    for args in (
        ["init", "-b", "main"],
        ["config", "user.email", "memovi@example.com"],
        ["config", "user.name", "Memovi Test"],
    ):
        subprocess.run(["git", *args], cwd=path, check=True, capture_output=True)
    (path / "file.txt").write_text("v1\n", encoding="utf-8")
    subprocess.run(["git", "add", "file.txt"], cwd=path, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=path, check=True, capture_output=True)
    return path


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


def _submit(
    engine: CapabilityExecutionEngine,
    arguments: dict[str, object],
    *,
    source: str = "acceptance",
):
    return engine.submit(
        CapabilityExecutionRequest.create(
            capability_id="git",
            workspace_id=WorkspaceId.default(),
            arguments=arguments,
            source=source,
        ),
        make_auth_context(),
    )


def test_1_detect_repository_returns_metadata(repo: Path) -> None:
    engine = _engine(repo.parent, mode=PermissionMode.ALWAYS_ALLOW)

    detect = _submit(
        engine,
        {"operation": "detect_repository", "repository": str(repo)},
    )
    assert detect.status is CapabilityExecutionStatus.COMPLETED
    assert detect.output is not None
    assert detect.output["is_repository"] is True
    assert Path(detect.output["root"]) == repo.resolve()

    info = _submit(
        engine,
        {"operation": "repository_info", "repository": str(repo)},
    )
    assert info.status is CapabilityExecutionStatus.COMPLETED
    assert info.output["branch"] == "main"
    assert info.output["detached"] is False
    assert info.output["head"]
    assert Path(info.output["root"]) == repo.resolve()
    assert info.output["git_dir"]


def test_2_status_reports_modified_staged_untracked(repo: Path) -> None:
    engine = _engine(repo.parent, mode=PermissionMode.ALWAYS_ALLOW)
    (repo / "file.txt").write_text("modified\n", encoding="utf-8")
    (repo / "untracked.txt").write_text("new\n", encoding="utf-8")
    subprocess.run(
        ["git", "add", "file.txt"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    (repo / "file.txt").write_text("modified-again\n", encoding="utf-8")

    status = _submit(engine, {"operation": "status", "repository": str(repo)})
    assert status.status is CapabilityExecutionStatus.COMPLETED
    assert status.output["branch"] == "main"
    assert "file.txt" in status.output["staged"]
    assert "file.txt" in status.output["modified"]
    assert "untracked.txt" in status.output["untracked"]
    assert status.output["clean"] is False
    assert "stdout" not in status.output


def test_3_list_branches_identifies_active_branch(repo: Path) -> None:
    engine = _engine(repo.parent, mode=PermissionMode.ALWAYS_ALLOW)
    result = _submit(engine, {"operation": "list_branches", "repository": str(repo)})

    assert result.status is CapabilityExecutionStatus.COMPLETED
    assert result.output["current"] == "main"
    names = {item["name"] for item in result.output["local"]}
    assert "main" in names
    current_entries = [item for item in result.output["local"] if item.get("current")]
    assert len(current_entries) == 1
    assert current_entries[0]["name"] == "main"


def test_4_create_branch_switch_and_switch_back(repo: Path) -> None:
    engine = _engine(repo.parent, mode=PermissionMode.ALWAYS_ALLOW)

    created = _submit(
        engine,
        {
            "operation": "create_branch",
            "repository": str(repo),
            "name": "acceptance-branch",
            "checkout": True,
        },
    )
    assert created.status is CapabilityExecutionStatus.COMPLETED
    assert created.output["branch"] == "acceptance-branch"
    assert created.output["current_branch"] == "acceptance-branch"

    listed = _submit(engine, {"operation": "list_branches", "repository": str(repo)})
    assert listed.output["current"] == "acceptance-branch"

    back = _submit(
        engine,
        {
            "operation": "checkout_branch",
            "repository": str(repo),
            "branch": "main",
        },
    )
    assert back.status is CapabilityExecutionStatus.COMPLETED
    assert back.output["branch"] == "main"

    listed_again = _submit(engine, {"operation": "list_branches", "repository": str(repo)})
    assert listed_again.output["current"] == "main"


def test_5_stage_modified_file_updates_status(repo: Path) -> None:
    engine = _engine(repo.parent, mode=PermissionMode.ALWAYS_ALLOW)
    (repo / "file.txt").write_text("staged-me\n", encoding="utf-8")

    before = _submit(engine, {"operation": "status", "repository": str(repo)})
    assert "file.txt" in before.output["modified"]
    assert "file.txt" not in before.output["staged"]

    staged = _submit(
        engine,
        {
            "operation": "stage_files",
            "repository": str(repo),
            "paths": ["file.txt"],
        },
    )
    assert staged.status is CapabilityExecutionStatus.COMPLETED
    assert staged.output["paths"] == ["file.txt"]

    after = _submit(engine, {"operation": "status", "repository": str(repo)})
    assert "file.txt" in after.output["staged"]


def test_6_commit_appears_in_history(repo: Path) -> None:
    engine = _engine(repo.parent, mode=PermissionMode.ALWAYS_ALLOW)
    (repo / "file.txt").write_text("commit-me\n", encoding="utf-8")
    _submit(
        engine,
        {
            "operation": "stage_files",
            "repository": str(repo),
            "paths": ["file.txt"],
        },
    )

    committed = _submit(
        engine,
        {
            "operation": "commit",
            "repository": str(repo),
            "message": "acceptance commit message",
        },
    )
    assert committed.status is CapabilityExecutionStatus.COMPLETED
    assert committed.output["message"] == "acceptance commit message"
    assert committed.output["short_sha"]
    assert committed.output["sha"]

    history = _submit(
        engine,
        {
            "operation": "commit_history",
            "repository": str(repo),
            "limit": 10,
        },
    )
    assert history.status is CapabilityExecutionStatus.COMPLETED
    subjects = [item["subject"] for item in history.output["commits"]]
    assert "acceptance commit message" in subjects
    shas = [item["sha"] for item in history.output["commits"]]
    assert committed.output["sha"] in shas


def test_7_diff_returns_structured_output(repo: Path) -> None:
    engine = _engine(repo.parent, mode=PermissionMode.ALWAYS_ALLOW)
    (repo / "file.txt").write_text("diff-body\n", encoding="utf-8")

    result = _submit(
        engine,
        {
            "operation": "diff",
            "repository": str(repo),
            "path": "file.txt",
        },
    )
    assert result.status is CapabilityExecutionStatus.COMPLETED
    assert result.output["operation"] == "diff"
    assert result.output["path"] == "file.txt"
    assert isinstance(result.output["patch"], str)
    assert "diff-body" in result.output["patch"]
    assert result.output["truncated"] is False
    assert "stdout" not in result.output
    assert "argv" not in result.output


def test_8_outside_repository_returns_normalized_error(repo: Path) -> None:
    engine = _engine(repo.parent, mode=PermissionMode.ALWAYS_ALLOW)
    empty = repo.parent / "not-a-repo"
    empty.mkdir()
    # Block parent worktree discovery so git reports not-a-repository.
    (empty / ".git").write_text("gitdir: /nonexistent-memovi-git-test\n", encoding="utf-8")

    result = _submit(
        engine,
        {"operation": "status", "repository": str(empty)},
    )
    assert result.status is CapabilityExecutionStatus.FAILED
    assert result.error is not None
    assert result.error.code == "not_a_git_repository"
    assert result.output is None


def test_9_confirmation_required_until_approved(repo: Path) -> None:
    engine = _engine(repo.parent, mode=PermissionMode.ASK_EVERY_TIME)

    pending = _submit(
        engine,
        {
            "operation": "commit",
            "repository": str(repo),
            "message": "needs approval",
            "allow_empty": True,
        },
    )
    assert pending.status is CapabilityExecutionStatus.PENDING_APPROVAL
    assert pending.output is None

    # Still pending — not executed yet.
    current = engine.get(pending.execution_id, workspace_id=WorkspaceId.default())
    assert current.status is CapabilityExecutionStatus.PENDING_APPROVAL

    approved = engine.approve(
        pending.execution_id,
        workspace_id=WorkspaceId.default(),
        context=make_auth_context(),
    )
    assert approved.status is CapabilityExecutionStatus.COMPLETED
    assert approved.output is not None
    assert approved.output["message"] == "needs approval"


def test_10_every_git_operation_creates_audit_entry(repo: Path) -> None:
    engine = _engine(repo.parent, mode=PermissionMode.ALWAYS_ALLOW)

    operations = (
        {"operation": "detect_repository", "repository": str(repo)},
        {"operation": "status", "repository": str(repo)},
        {"operation": "list_branches", "repository": str(repo)},
        {"operation": "commit_history", "repository": str(repo), "limit": 3},
    )
    for arguments in operations:
        result = _submit(engine, arguments)
        assert result.status is CapabilityExecutionStatus.COMPLETED

    audit = engine.list_audit(workspace_id=WorkspaceId.default())
    completed = [
        entry
        for entry in audit
        if entry.capability_id == "git" and entry.status is CapabilityExecutionStatus.COMPLETED
    ]
    completed_ops = {entry.arguments.get("operation") for entry in completed}
    assert completed_ops >= {
        "detect_repository",
        "status",
        "list_branches",
        "commit_history",
    }
    for entry in completed:
        assert entry.workspace_id == str(WorkspaceId.default())
        assert entry.arguments.get("repository") == str(repo)
        assert entry.timestamp is not None
        assert entry.duration >= 0
        assert entry.result_summary.get("status") == "completed"


def test_acceptance_write_requires_git_write(repo: Path) -> None:
    registry = CapabilityRegistry()
    register_git_capability(
        registry,
        GitCapabilityConfig.from_roots([repo.parent]),
    )
    invoker = CapabilityInvoker(registry=registry)
    result = invoker.invoke(
        CapabilityRequest.create(
            capability_id="git",
            arguments={
                "operation": "stage_files",
                "repository": str(repo),
                "paths": ["file.txt"],
            },
        ),
        CapabilityContext.create(
            workspace_id=WorkspaceId.default(),
            granted_permissions=frozenset({GIT_READ}),
        ),
    )
    assert result.success is False
    assert result.error.code == "permission_denied"

    network = invoker.invoke(
        CapabilityRequest.create(
            capability_id="git",
            arguments={"operation": "push", "repository": str(repo)},
        ),
        CapabilityContext.create(
            workspace_id=WorkspaceId.default(),
            granted_permissions=frozenset({GIT_READ, GIT_WRITE}),
        ),
    )
    assert network.success is False
    assert network.error.details["permission"] == GIT_NETWORK.name
