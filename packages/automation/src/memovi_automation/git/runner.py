"""Private git CLI runner for the Git Capability.

Uses argv-based subprocess invocation (never shell=True). Never returns raw
process objects or unparsed CLI dumps to callers.
"""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import threading
import time
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter

from memovi_automation.domain.exceptions import (
    CapabilityCancelledError,
    CapabilityExecutionError,
)
from memovi_automation.domain.value_objects.cancellation_token import CancellationToken
from memovi_automation.git.errors import (
    AUTHENTICATION_FAILURE,
    DETACHED_HEAD,
    GIT_FAILED,
    GIT_NOT_AVAILABLE,
    MERGE_CONFLICT,
    PUSH_REJECTED,
    TIMEOUT,
)


@dataclass(frozen=True, slots=True)
class GitCliResult:
    argv: tuple[str, ...]
    exit_code: int
    stdout: str
    stderr: str
    duration_seconds: float


def run_git(
    args: Sequence[str],
    *,
    repository: Path,
    git_executable: str,
    timeout_seconds: float,
    cancellation: CancellationToken,
    check: bool = True,
) -> GitCliResult:
    """Run ``git <args>`` in ``repository`` and return structured capture."""
    argv = [git_executable, *args]
    env = os.environ.copy()
    # Keep git non-interactive and locale-stable for parsing.
    env.setdefault("GIT_TERMINAL_PROMPT", "0")
    env.setdefault("LC_ALL", "C")

    started = perf_counter()
    try:
        process = subprocess.Popen(
            argv,
            cwd=str(repository),
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            **_spawn_kwargs(),
        )
    except FileNotFoundError as exc:
        raise CapabilityExecutionError(
            "Git executable is not available on this host.",
            code=GIT_NOT_AVAILABLE,
            details={"git_executable": git_executable},
        ) from exc
    except OSError as exc:
        raise CapabilityExecutionError(
            f"Failed to start git: {exc}",
            code=GIT_FAILED,
            details={"os_error": type(exc).__name__},
        ) from exc

    captured: dict[str, str] = {"stdout": "", "stderr": ""}
    done = threading.Event()

    def _communicate() -> None:
        try:
            stdout, stderr = process.communicate()
            captured["stdout"] = stdout or ""
            captured["stderr"] = stderr or ""
        except Exception:
            captured["stdout"] = ""
            captured["stderr"] = ""
        finally:
            done.set()

    reader = threading.Thread(target=_communicate, name="git-communicate", daemon=True)
    reader.start()

    try:
        deadline = time.monotonic() + timeout_seconds
        while not done.wait(0.05):
            if cancellation.is_cancelled:
                _terminate_process(process)
                raise CapabilityCancelledError("Git operation was cancelled.")
            if time.monotonic() >= deadline:
                _terminate_process(process)
                raise CapabilityExecutionError(
                    f"Git operation timed out after {timeout_seconds} seconds.",
                    code=TIMEOUT,
                    details={"timeout_seconds": timeout_seconds, "argv": list(argv)},
                )

        reader.join(timeout=1.0)
        exit_code = process.returncode if process.returncode is not None else -1
        duration = perf_counter() - started
        result = GitCliResult(
            argv=tuple(argv),
            exit_code=exit_code,
            stdout=captured["stdout"],
            stderr=captured["stderr"],
            duration_seconds=duration,
        )
        if check and exit_code != 0:
            raise _normalize_git_failure(result)
        return result
    finally:
        if process.poll() is None:
            _terminate_process(process)
        _close_streams(process)
        done.wait(0.2)


def _normalize_git_failure(result: GitCliResult) -> CapabilityExecutionError:
    combined = f"{result.stdout}\n{result.stderr}".lower()
    code = GIT_FAILED
    message = "Git operation failed."

    if "not a git repository" in combined:
        code = "not_a_git_repository"
        message = "Path is not a git repository."
    elif "conflict" in combined or "merge conflict" in combined:
        code = MERGE_CONFLICT
        message = "Git reported a merge conflict."
    elif "authentication failed" in combined or "could not read username" in combined:
        code = AUTHENTICATION_FAILURE
        message = "Git authentication failed."
    elif "detached head" in combined:
        code = DETACHED_HEAD
        message = "Repository is in a detached HEAD state."
    elif "rejected" in combined and "push" in " ".join(result.argv).lower():
        code = PUSH_REJECTED
        message = "Git push was rejected."
    elif result.stderr.strip():
        # Prefer a short stderr line without dumping the full CLI transcript.
        first_line = result.stderr.strip().splitlines()[0][:240]
        message = f"Git operation failed: {first_line}"

    return CapabilityExecutionError(
        message,
        code=code,
        details={
            "exit_code": result.exit_code,
            "stderr_summary": result.stderr.strip()[:500],
        },
    )


def _spawn_kwargs() -> dict[str, object]:
    if sys.platform == "win32":
        return {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP}  # type: ignore[attr-defined]
    return {"start_new_session": True}


def _close_streams(process: subprocess.Popen[str]) -> None:
    for stream in (process.stdout, process.stderr, process.stdin):
        if stream is None:
            continue
        try:
            stream.close()
        except OSError:
            continue


def _terminate_process(process: subprocess.Popen[str]) -> None:
    if process.poll() is not None:
        return
    try:
        if sys.platform == "win32":
            subprocess.run(
                ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                check=False,
                capture_output=True,
            )
        else:
            try:
                os.killpg(process.pid, signal.SIGTERM)
            except ProcessLookupError:
                process.terminate()
    except OSError:
        try:
            process.kill()
        except OSError:
            return
    try:
        process.wait(timeout=1.0)
    except subprocess.TimeoutExpired:
        try:
            process.kill()
        except OSError:
            pass
