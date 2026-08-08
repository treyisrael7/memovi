import subprocess
from pathlib import Path

import pytest
from memovi_automation import (
    GIT_NETWORK,
    GIT_READ,
    GIT_WRITE,
    CapabilityContext,
    CapabilityInvoker,
    CapabilityRegistry,
    CapabilityRequest,
    GitCapabilityConfig,
    register_git_capability,
)
from memovi_automation.git import CAPABILITY_ID, NOT_A_GIT_REPOSITORY
from memovi_shared import WorkspaceId


def _git_available() -> bool:
    try:
        subprocess.run(
            ["git", "--version"],
            check=True,
            capture_output=True,
            text=True,
        )
        return True
    except OSError, subprocess.CalledProcessError:
        return False


pytestmark = pytest.mark.skipif(not _git_available(), reason="git CLI unavailable")


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    root = tmp_path / "workspace"
    root.mkdir()
    repo_path = root / "project"
    repo_path.mkdir()
    _run_git(repo_path, "init", "-b", "main")
    _run_git(repo_path, "config", "user.email", "memovi@example.com")
    _run_git(repo_path, "config", "user.name", "Memovi Test")
    (repo_path / "README.md").write_text("# project\n", encoding="utf-8")
    _run_git(repo_path, "add", "README.md")
    _run_git(repo_path, "commit", "-m", "initial")
    return repo_path


def _run_git(cwd: Path, *args: str) -> None:
    subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    )


def _stack_for_repo(repo: Path):
    workspace = repo.parent
    registry = CapabilityRegistry()
    capability = register_git_capability(
        registry,
        GitCapabilityConfig.from_roots([workspace]),
    )
    return registry, CapabilityInvoker(registry=registry), capability


def _context(*, granted=frozenset({GIT_READ, GIT_WRITE, GIT_NETWORK})) -> CapabilityContext:
    return CapabilityContext.create(
        workspace_id=WorkspaceId.default(),
        granted_permissions=granted,
        correlation_id="git-test",
    )


def _invoke(invoker: CapabilityInvoker, *, arguments: dict, granted=None):
    return invoker.invoke(
        CapabilityRequest.create(capability_id=CAPABILITY_ID, arguments=arguments),
        _context(
            granted=frozenset({GIT_READ, GIT_WRITE, GIT_NETWORK}) if granted is None else granted
        ),
    )


def test_git_capability_is_discoverable(repo: Path) -> None:
    registry, _invoker, capability = _stack_for_repo(repo)
    assert registry.contains("git")
    metadata = registry.metadata("git")
    assert metadata.id == CAPABILITY_ID
    assert "git.read" in metadata.permission_names()
    assert "git.write" in metadata.permission_names()
    assert "git.network" in metadata.permission_names()
    assert registry.get("git") is capability


def test_detect_and_repository_info(repo: Path) -> None:
    _registry, invoker, _cap = _stack_for_repo(repo)
    detect = _invoke(
        invoker,
        arguments={"operation": "detect_repository", "repository": str(repo)},
    )
    assert detect.success is True
    assert detect.output["is_repository"] is True

    info = _invoke(
        invoker,
        arguments={"operation": "repository_info", "repository": str(repo)},
    )
    assert info.success is True
    assert info.output["branch"] == "main"
    assert Path(info.output["root"]) == repo.resolve()


def test_status_lists_modified_staged_untracked(repo: Path) -> None:
    _registry, invoker, _cap = _stack_for_repo(repo)
    (repo / "README.md").write_text("# changed\n", encoding="utf-8")
    (repo / "new.txt").write_text("new", encoding="utf-8")
    _run_git(repo, "add", "README.md")

    result = _invoke(
        invoker,
        arguments={"operation": "status", "repository": str(repo)},
    )
    assert result.success is True
    assert result.output["branch"] == "main"
    assert "README.md" in result.output["staged"]
    assert "new.txt" in result.output["untracked"]
    assert result.output["clean"] is False


def test_list_branches_and_create_checkout(repo: Path) -> None:
    _registry, invoker, _cap = _stack_for_repo(repo)
    created = _invoke(
        invoker,
        arguments={
            "operation": "create_branch",
            "repository": str(repo),
            "name": "feature",
            "checkout": True,
        },
    )
    assert created.success is True
    assert created.output["branch"] == "feature"

    listed = _invoke(
        invoker,
        arguments={"operation": "list_branches", "repository": str(repo)},
    )
    assert listed.success is True
    names = {item["name"] for item in listed.output["local"]}
    assert names >= {"main", "feature"}
    assert listed.output["current"] == "feature"

    checked = _invoke(
        invoker,
        arguments={
            "operation": "checkout_branch",
            "repository": str(repo),
            "branch": "main",
        },
    )
    assert checked.success is True
    assert checked.output["branch"] == "main"


def test_stage_unstage_commit_and_history(repo: Path) -> None:
    _registry, invoker, _cap = _stack_for_repo(repo)
    (repo / "note.txt").write_text("hello", encoding="utf-8")

    staged = _invoke(
        invoker,
        arguments={
            "operation": "stage_files",
            "repository": str(repo),
            "paths": ["note.txt"],
        },
    )
    assert staged.success is True

    unstaged = _invoke(
        invoker,
        arguments={
            "operation": "unstage_files",
            "repository": str(repo),
            "paths": ["note.txt"],
        },
    )
    assert unstaged.success is True

    _invoke(
        invoker,
        arguments={
            "operation": "stage_files",
            "repository": str(repo),
            "paths": ["note.txt"],
        },
    )
    committed = _invoke(
        invoker,
        arguments={
            "operation": "commit",
            "repository": str(repo),
            "message": "add note",
        },
    )
    assert committed.success is True
    assert committed.output["short_sha"]
    assert committed.output["message"] == "add note"

    history = _invoke(
        invoker,
        arguments={
            "operation": "commit_history",
            "repository": str(repo),
            "limit": 5,
        },
    )
    assert history.success is True
    assert history.output["count"] >= 2
    subjects = [item["subject"] for item in history.output["commits"]]
    assert "add note" in subjects


def test_diff_returns_structured_patch(repo: Path) -> None:
    _registry, invoker, _cap = _stack_for_repo(repo)
    (repo / "README.md").write_text("# changed for diff\n", encoding="utf-8")
    result = _invoke(
        invoker,
        arguments={"operation": "diff", "repository": str(repo)},
    )
    assert result.success is True
    assert "changed for diff" in result.output["patch"]
    assert result.output["truncated"] is False


def test_not_a_repository_is_structured(repo: Path) -> None:
    workspace = repo.parent
    empty = workspace / "empty"
    empty.mkdir()
    # Block parent worktree discovery (e.g. a .git under the user home) so this
    # path is treated as outside any repository while remaining under allowed roots.
    (empty / ".git").write_text("gitdir: /nonexistent-memovi-git-test\n", encoding="utf-8")
    _registry, invoker, _cap = _stack_for_repo(repo)
    result = _invoke(
        invoker,
        arguments={"operation": "status", "repository": str(empty)},
    )
    assert result.success is False
    assert result.error is not None
    assert result.error.code == NOT_A_GIT_REPOSITORY


def test_read_permission_blocks_write(repo: Path) -> None:
    _registry, invoker, _cap = _stack_for_repo(repo)
    result = _invoke(
        invoker,
        arguments={
            "operation": "commit",
            "repository": str(repo),
            "message": "nope",
            "allow_empty": True,
        },
        granted=frozenset({GIT_READ}),
    )
    assert result.success is False
    assert result.error is not None
    assert result.error.code == "permission_denied"


def test_network_permission_required_for_fetch(repo: Path) -> None:
    _registry, invoker, _cap = _stack_for_repo(repo)
    result = _invoke(
        invoker,
        arguments={"operation": "fetch", "repository": str(repo)},
        granted=frozenset({GIT_READ, GIT_WRITE}),
    )
    assert result.success is False
    assert result.error is not None
    assert result.error.code == "permission_denied"
    assert result.error.details["permission"] == "git.network"
