"""Structured Git operation implementations (CLI details stay private)."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any

from memovi_automation.domain.exceptions import CapabilityExecutionError
from memovi_automation.domain.value_objects.cancellation_token import CancellationToken
from memovi_automation.git.config import GitCapabilityConfig
from memovi_automation.git.errors import (
    EMPTY_MESSAGE,
    INVALID_PATHS,
    INVALID_REF,
    NOT_A_GIT_REPOSITORY,
)
from memovi_automation.git.runner import GitCliResult, run_git


def detect_repository(
    repository: Path,
    *,
    config: GitCapabilityConfig,
    timeout_seconds: float,
    cancellation: CancellationToken,
) -> dict[str, Any]:
    result = run_git(
        ["rev-parse", "--is-inside-work-tree"],
        repository=repository,
        git_executable=config.git_executable,
        timeout_seconds=timeout_seconds,
        cancellation=cancellation,
        check=False,
    )
    is_repo = result.exit_code == 0 and result.stdout.strip().lower() == "true"
    payload: dict[str, Any] = {
        "operation": "detect_repository",
        "repository": str(repository),
        "success": True,
        "is_repository": is_repo,
        "metadata": {"is_repository": is_repo},
    }
    if not is_repo:
        return payload
    info = repository_info(
        repository,
        config=config,
        timeout_seconds=timeout_seconds,
        cancellation=cancellation,
    )
    payload["root"] = info["root"]
    payload["git_dir"] = info["git_dir"]
    return payload


def repository_info(
    repository: Path,
    *,
    config: GitCapabilityConfig,
    timeout_seconds: float,
    cancellation: CancellationToken,
) -> dict[str, Any]:
    _ensure_repository(repository, config=config, timeout_seconds=timeout_seconds, cancellation=cancellation)
    root = run_git(
        ["rev-parse", "--show-toplevel"],
        repository=repository,
        git_executable=config.git_executable,
        timeout_seconds=timeout_seconds,
        cancellation=cancellation,
    ).stdout.strip()
    git_dir = run_git(
        ["rev-parse", "--git-dir"],
        repository=repository,
        git_executable=config.git_executable,
        timeout_seconds=timeout_seconds,
        cancellation=cancellation,
    ).stdout.strip()
    git_dir_path = Path(git_dir)
    if not git_dir_path.is_absolute():
        git_dir_path = (repository / git_dir_path).resolve()
    branch_info = _current_branch_state(
        repository,
        config=config,
        timeout_seconds=timeout_seconds,
        cancellation=cancellation,
    )
    return {
        "operation": "repository_info",
        "repository": str(repository),
        "success": True,
        "root": str(Path(root).resolve()),
        "git_dir": str(git_dir_path),
        "branch": branch_info["branch"],
        "detached": branch_info["detached"],
        "head": branch_info["head"],
        "metadata": {
            "root": str(Path(root).resolve()),
            "branch": branch_info["branch"],
            "detached": branch_info["detached"],
        },
    }


def status(
    repository: Path,
    *,
    config: GitCapabilityConfig,
    timeout_seconds: float,
    cancellation: CancellationToken,
    include_ignored: bool = False,
) -> dict[str, Any]:
    _ensure_repository(repository, config=config, timeout_seconds=timeout_seconds, cancellation=cancellation)
    args = ["status", "--porcelain=v1", "-b"]
    if include_ignored:
        args.append("--ignored")
    result = run_git(
        args,
        repository=repository,
        git_executable=config.git_executable,
        timeout_seconds=timeout_seconds,
        cancellation=cancellation,
    )
    parsed = _parse_status_porcelain(result.stdout)
    branch_info = _current_branch_state(
        repository,
        config=config,
        timeout_seconds=timeout_seconds,
        cancellation=cancellation,
    )
    clean = not (
        parsed["staged"]
        or parsed["modified"]
        or parsed["untracked"]
        or parsed["conflicted"]
    )
    return {
        "operation": "status",
        "repository": str(repository),
        "success": True,
        "branch": branch_info["branch"],
        "detached": branch_info["detached"],
        "head": branch_info["head"],
        "upstream": parsed.get("upstream"),
        "ahead": parsed.get("ahead", 0),
        "behind": parsed.get("behind", 0),
        "clean": clean,
        "staged": parsed["staged"],
        "modified": parsed["modified"],
        "untracked": parsed["untracked"],
        "ignored": parsed["ignored"],
        "conflicted": parsed["conflicted"],
        "metadata": {
            "branch": branch_info["branch"],
            "clean": clean,
            "staged_count": len(parsed["staged"]),
            "modified_count": len(parsed["modified"]),
            "untracked_count": len(parsed["untracked"]),
        },
    }


def list_branches(
    repository: Path,
    *,
    config: GitCapabilityConfig,
    timeout_seconds: float,
    cancellation: CancellationToken,
) -> dict[str, Any]:
    _ensure_repository(repository, config=config, timeout_seconds=timeout_seconds, cancellation=cancellation)
    local_result = run_git(
        ["for-each-ref", "--format=%(refname:short)%00%(HEAD)%00%(objectname:short)", "refs/heads"],
        repository=repository,
        git_executable=config.git_executable,
        timeout_seconds=timeout_seconds,
        cancellation=cancellation,
    )
    remote_result = run_git(
        [
            "for-each-ref",
            "--format=%(refname:short)%00%(objectname:short)",
            "refs/remotes",
        ],
        repository=repository,
        git_executable=config.git_executable,
        timeout_seconds=timeout_seconds,
        cancellation=cancellation,
    )
    local: list[dict[str, Any]] = []
    remote: list[dict[str, Any]] = []
    current: str | None = None
    for line in local_result.stdout.splitlines():
        parts = line.split("\x00")
        if len(parts) < 3:
            continue
        name, head_marker, sha = parts[0], parts[1], parts[2]
        entry = {"name": name, "sha": sha, "current": head_marker == "*"}
        if head_marker == "*":
            current = name
        local.append(entry)
    for line in remote_result.stdout.splitlines():
        parts = line.split("\x00")
        if len(parts) < 2:
            continue
        remote.append({"name": parts[0], "sha": parts[1]})

    return {
        "operation": "list_branches",
        "repository": str(repository),
        "success": True,
        "current": current,
        "local": local,
        "remote": remote,
        "metadata": {
            "current": current,
            "local_count": len(local),
            "remote_count": len(remote),
        },
    }


def checkout_branch(
    repository: Path,
    *,
    branch: str,
    config: GitCapabilityConfig,
    timeout_seconds: float,
    cancellation: CancellationToken,
) -> dict[str, Any]:
    _ensure_repository(repository, config=config, timeout_seconds=timeout_seconds, cancellation=cancellation)
    name = _require_ref(branch, argument="branch")
    run_git(
        ["checkout", name],
        repository=repository,
        git_executable=config.git_executable,
        timeout_seconds=timeout_seconds,
        cancellation=cancellation,
    )
    state = _current_branch_state(
        repository,
        config=config,
        timeout_seconds=timeout_seconds,
        cancellation=cancellation,
    )
    return {
        "operation": "checkout_branch",
        "repository": str(repository),
        "success": True,
        "branch": state["branch"],
        "detached": state["detached"],
        "head": state["head"],
        "metadata": {"branch": state["branch"], "detached": state["detached"]},
    }


def create_branch(
    repository: Path,
    *,
    name: str,
    start_point: str | None,
    checkout: bool,
    config: GitCapabilityConfig,
    timeout_seconds: float,
    cancellation: CancellationToken,
) -> dict[str, Any]:
    _ensure_repository(repository, config=config, timeout_seconds=timeout_seconds, cancellation=cancellation)
    branch = _require_ref(name, argument="name")
    args = ["branch", branch]
    if start_point:
        args.append(_require_ref(start_point, argument="start_point"))
    run_git(
        args,
        repository=repository,
        git_executable=config.git_executable,
        timeout_seconds=timeout_seconds,
        cancellation=cancellation,
    )
    if checkout:
        run_git(
            ["checkout", branch],
            repository=repository,
            git_executable=config.git_executable,
            timeout_seconds=timeout_seconds,
            cancellation=cancellation,
        )
    state = _current_branch_state(
        repository,
        config=config,
        timeout_seconds=timeout_seconds,
        cancellation=cancellation,
    )
    return {
        "operation": "create_branch",
        "repository": str(repository),
        "success": True,
        "branch": branch,
        "checked_out": checkout,
        "current_branch": state["branch"],
        "metadata": {"branch": branch, "checked_out": checkout},
    }


def stage_files(
    repository: Path,
    *,
    paths: Sequence[str],
    config: GitCapabilityConfig,
    timeout_seconds: float,
    cancellation: CancellationToken,
) -> dict[str, Any]:
    _ensure_repository(repository, config=config, timeout_seconds=timeout_seconds, cancellation=cancellation)
    normalized = _require_paths(paths)
    run_git(
        ["add", "--", *normalized],
        repository=repository,
        git_executable=config.git_executable,
        timeout_seconds=timeout_seconds,
        cancellation=cancellation,
    )
    return {
        "operation": "stage_files",
        "repository": str(repository),
        "success": True,
        "paths": list(normalized),
        "metadata": {"path_count": len(normalized)},
    }


def unstage_files(
    repository: Path,
    *,
    paths: Sequence[str],
    config: GitCapabilityConfig,
    timeout_seconds: float,
    cancellation: CancellationToken,
) -> dict[str, Any]:
    _ensure_repository(repository, config=config, timeout_seconds=timeout_seconds, cancellation=cancellation)
    normalized = _require_paths(paths)
    # Preferred modern form; falls back for older git.
    result = run_git(
        ["restore", "--staged", "--", *normalized],
        repository=repository,
        git_executable=config.git_executable,
        timeout_seconds=timeout_seconds,
        cancellation=cancellation,
        check=False,
    )
    if result.exit_code != 0:
        run_git(
            ["reset", "HEAD", "--", *normalized],
            repository=repository,
            git_executable=config.git_executable,
            timeout_seconds=timeout_seconds,
            cancellation=cancellation,
        )
    return {
        "operation": "unstage_files",
        "repository": str(repository),
        "success": True,
        "paths": list(normalized),
        "metadata": {"path_count": len(normalized)},
    }


def commit(
    repository: Path,
    *,
    message: str,
    config: GitCapabilityConfig,
    timeout_seconds: float,
    cancellation: CancellationToken,
    allow_empty: bool = False,
) -> dict[str, Any]:
    _ensure_repository(repository, config=config, timeout_seconds=timeout_seconds, cancellation=cancellation)
    if not isinstance(message, str) or not message.strip():
        raise CapabilityExecutionError(
            "Commit message is required.",
            code=EMPTY_MESSAGE,
            details={"argument": "message"},
        )
    args = ["commit", "-m", message.strip()]
    if allow_empty:
        args.append("--allow-empty")
    result = run_git(
        args,
        repository=repository,
        git_executable=config.git_executable,
        timeout_seconds=timeout_seconds,
        cancellation=cancellation,
    )
    sha = run_git(
        ["rev-parse", "HEAD"],
        repository=repository,
        git_executable=config.git_executable,
        timeout_seconds=timeout_seconds,
        cancellation=cancellation,
    ).stdout.strip()
    short = sha[:7] if sha else ""
    return {
        "operation": "commit",
        "repository": str(repository),
        "success": True,
        "sha": sha,
        "short_sha": short,
        "message": message.strip(),
        "summary": result.stdout.strip().splitlines()[0] if result.stdout.strip() else short,
        "metadata": {"sha": sha, "short_sha": short},
    }


def commit_history(
    repository: Path,
    *,
    limit: int,
    ref: str | None,
    config: GitCapabilityConfig,
    timeout_seconds: float,
    cancellation: CancellationToken,
) -> dict[str, Any]:
    _ensure_repository(repository, config=config, timeout_seconds=timeout_seconds, cancellation=cancellation)
    args = [
        "log",
        f"-n{limit}",
        "--format=%H%x00%h%x00%an%x00%aI%x00%s",
    ]
    if ref:
        args.append(_require_ref(ref, argument="ref"))
    result = run_git(
        args,
        repository=repository,
        git_executable=config.git_executable,
        timeout_seconds=timeout_seconds,
        cancellation=cancellation,
    )
    commits: list[dict[str, str]] = []
    for line in result.stdout.splitlines():
        parts = line.split("\x00")
        if len(parts) < 5:
            continue
        commits.append(
            {
                "sha": parts[0],
                "short_sha": parts[1],
                "author": parts[2],
                "date": parts[3],
                "subject": parts[4],
            }
        )
    return {
        "operation": "commit_history",
        "repository": str(repository),
        "success": True,
        "commits": commits,
        "count": len(commits),
        "ref": ref,
        "metadata": {"count": len(commits), "ref": ref},
    }


def fetch(
    repository: Path,
    *,
    remote: str | None,
    config: GitCapabilityConfig,
    timeout_seconds: float,
    cancellation: CancellationToken,
) -> dict[str, Any]:
    _ensure_repository(repository, config=config, timeout_seconds=timeout_seconds, cancellation=cancellation)
    args = ["fetch"]
    if remote:
        args.append(_require_ref(remote, argument="remote"))
    result = run_git(
        args,
        repository=repository,
        git_executable=config.git_executable,
        timeout_seconds=timeout_seconds,
        cancellation=cancellation,
    )
    return {
        "operation": "fetch",
        "repository": str(repository),
        "success": True,
        "remote": remote or "origin",
        "summary": _compact_output(result),
        "metadata": {"remote": remote or "origin"},
    }


def pull(
    repository: Path,
    *,
    remote: str | None,
    branch: str | None,
    config: GitCapabilityConfig,
    timeout_seconds: float,
    cancellation: CancellationToken,
) -> dict[str, Any]:
    _ensure_repository(repository, config=config, timeout_seconds=timeout_seconds, cancellation=cancellation)
    args = ["pull"]
    if remote:
        args.append(_require_ref(remote, argument="remote"))
        if branch:
            args.append(_require_ref(branch, argument="branch"))
    result = run_git(
        args,
        repository=repository,
        git_executable=config.git_executable,
        timeout_seconds=timeout_seconds,
        cancellation=cancellation,
    )
    return {
        "operation": "pull",
        "repository": str(repository),
        "success": True,
        "remote": remote,
        "branch": branch,
        "summary": _compact_output(result),
        "metadata": {"remote": remote, "branch": branch},
    }


def push(
    repository: Path,
    *,
    remote: str | None,
    branch: str | None,
    set_upstream: bool,
    config: GitCapabilityConfig,
    timeout_seconds: float,
    cancellation: CancellationToken,
) -> dict[str, Any]:
    _ensure_repository(repository, config=config, timeout_seconds=timeout_seconds, cancellation=cancellation)
    args = ["push"]
    if set_upstream:
        args.append("-u")
    if remote:
        args.append(_require_ref(remote, argument="remote"))
        if branch:
            args.append(_require_ref(branch, argument="branch"))
    result = run_git(
        args,
        repository=repository,
        git_executable=config.git_executable,
        timeout_seconds=timeout_seconds,
        cancellation=cancellation,
    )
    return {
        "operation": "push",
        "repository": str(repository),
        "success": True,
        "remote": remote,
        "branch": branch,
        "set_upstream": set_upstream,
        "summary": _compact_output(result),
        "metadata": {"remote": remote, "branch": branch},
    }


def diff(
    repository: Path,
    *,
    path: str | None,
    staged: bool,
    config: GitCapabilityConfig,
    timeout_seconds: float,
    cancellation: CancellationToken,
) -> dict[str, Any]:
    _ensure_repository(repository, config=config, timeout_seconds=timeout_seconds, cancellation=cancellation)
    args = ["diff", "--no-ext-diff"]
    if staged:
        args.append("--cached")
    if path:
        args.extend(["--", path.strip()])
    result = run_git(
        args,
        repository=repository,
        git_executable=config.git_executable,
        timeout_seconds=timeout_seconds,
        cancellation=cancellation,
    )
    patch = result.stdout
    truncated = False
    encoded = patch.encode("utf-8", errors="replace")
    if len(encoded) > config.max_diff_bytes:
        patch = encoded[: config.max_diff_bytes].decode("utf-8", errors="replace")
        truncated = True
    return {
        "operation": "diff",
        "repository": str(repository),
        "success": True,
        "path": path,
        "staged": staged,
        "patch": patch,
        "truncated": truncated,
        "metadata": {
            "staged": staged,
            "truncated": truncated,
            "size_bytes": len(encoded),
        },
    }


def _ensure_repository(
    repository: Path,
    *,
    config: GitCapabilityConfig,
    timeout_seconds: float,
    cancellation: CancellationToken,
) -> None:
    result = run_git(
        ["rev-parse", "--is-inside-work-tree"],
        repository=repository,
        git_executable=config.git_executable,
        timeout_seconds=timeout_seconds,
        cancellation=cancellation,
        check=False,
    )
    if result.exit_code != 0 or result.stdout.strip().lower() != "true":
        raise CapabilityExecutionError(
            f"Path is not a git repository: {repository}",
            code=NOT_A_GIT_REPOSITORY,
            details={"repository": str(repository)},
        )


def _current_branch_state(
    repository: Path,
    *,
    config: GitCapabilityConfig,
    timeout_seconds: float,
    cancellation: CancellationToken,
) -> dict[str, Any]:
    head = run_git(
        ["rev-parse", "HEAD"],
        repository=repository,
        git_executable=config.git_executable,
        timeout_seconds=timeout_seconds,
        cancellation=cancellation,
        check=False,
    )
    head_sha = head.stdout.strip() if head.exit_code == 0 else None
    symbolic = run_git(
        ["symbolic-ref", "--quiet", "--short", "HEAD"],
        repository=repository,
        git_executable=config.git_executable,
        timeout_seconds=timeout_seconds,
        cancellation=cancellation,
        check=False,
    )
    if symbolic.exit_code == 0 and symbolic.stdout.strip():
        return {
            "branch": symbolic.stdout.strip(),
            "detached": False,
            "head": head_sha,
        }
    if head_sha:
        return {
            "branch": None,
            "detached": True,
            "head": head_sha,
        }
    return {"branch": None, "detached": False, "head": None}


def _parse_status_porcelain(stdout: str) -> dict[str, Any]:
    staged: list[str] = []
    modified: list[str] = []
    untracked: list[str] = []
    ignored: list[str] = []
    conflicted: list[str] = []
    upstream: str | None = None
    ahead = 0
    behind = 0

    for raw_line in stdout.splitlines():
        if not raw_line:
            continue
        if raw_line.startswith("##"):
            header = raw_line[2:].strip()
            # e.g. main...origin/main [ahead 1, behind 2]
            if "..." in header:
                branch_part, _, rest = header.partition("...")
                upstream_part = rest.split(" ", 1)[0]
                upstream = upstream_part or None
                _ = branch_part
            if "[ahead " in header or "[behind " in header or "[ahead " in header:
                ahead, behind = _parse_ahead_behind(header)
            continue
        if len(raw_line) < 3:
            continue
        x, y = raw_line[0], raw_line[1]
        path = raw_line[3:]
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        if x == "?" and y == "?":
            untracked.append(path)
            continue
        if x == "!" and y == "!":
            ignored.append(path)
            continue
        if x in {"U", "A", "D"} and y in {"U", "A", "D"} and (x == "U" or y == "U"):
            conflicted.append(path)
        if x not in {" ", "?"}:
            staged.append(path)
        if y not in {" ", "?"}:
            modified.append(path)

    return {
        "staged": staged,
        "modified": modified,
        "untracked": untracked,
        "ignored": ignored,
        "conflicted": conflicted,
        "upstream": upstream,
        "ahead": ahead,
        "behind": behind,
    }


def _parse_ahead_behind(header: str) -> tuple[int, int]:
    ahead = 0
    behind = 0
    if "ahead " in header:
        try:
            ahead = int(header.split("ahead ", 1)[1].split("]", 1)[0].split(",", 1)[0].strip())
        except ValueError:
            ahead = 0
    if "behind " in header:
        try:
            behind = int(header.split("behind ", 1)[1].split("]", 1)[0].split(",", 1)[0].strip())
        except ValueError:
            behind = 0
    return ahead, behind


def _require_ref(value: str, *, argument: str) -> str:
    text = value.strip()
    if not text:
        raise CapabilityExecutionError(
            f"Argument '{argument}' must be a non-empty string.",
            code=INVALID_REF,
            details={"argument": argument},
        )
    if "\x00" in text or "\n" in text:
        raise CapabilityExecutionError(
            f"Argument '{argument}' contains invalid characters.",
            code=INVALID_REF,
            details={"argument": argument},
        )
    return text


def _require_paths(paths: object) -> list[str]:
    if not isinstance(paths, (list, tuple)) or not paths:
        raise CapabilityExecutionError(
            "Argument 'paths' must be a non-empty array of strings.",
            code=INVALID_PATHS,
            details={"argument": "paths"},
        )
    normalized: list[str] = []
    for item in paths:
        if not isinstance(item, str) or not item.strip():
            raise CapabilityExecutionError(
                "Each path in 'paths' must be a non-empty string.",
                code=INVALID_PATHS,
                details={"argument": "paths"},
            )
        normalized.append(item.strip())
    return normalized


def _compact_output(result: GitCliResult) -> str:
    text = (result.stdout or result.stderr or "").strip()
    if not text:
        return "ok"
    return text.splitlines()[0][:240]
