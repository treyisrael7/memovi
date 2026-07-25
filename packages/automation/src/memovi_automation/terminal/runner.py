"""OS process runner for the Terminal Capability.

Keeps subprocess details out of the capability surface. Never returns raw
process objects — only structured capture results.
"""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import threading
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter

from memovi_automation.domain.exceptions import (
    CapabilityCancelledError,
    CapabilityExecutionError,
)
from memovi_automation.domain.value_objects.cancellation_token import CancellationToken
from memovi_automation.terminal.errors import PROCESS_FAILED, TIMEOUT

ProgressCallback = Callable[[Mapping[str, object]], None]


@dataclass(frozen=True, slots=True)
class ProcessCapture:
    """Structured process outcome — no raw Popen / handle exposure."""

    command: str
    working_directory: str
    exit_code: int | None
    stdout: str
    stderr: str
    duration_seconds: float
    timed_out: bool
    cancelled: bool
    stdout_truncated: bool
    stderr_truncated: bool


def run_command(
    command: str,
    *,
    working_directory: Path,
    env: Mapping[str, str] | None,
    timeout_seconds: float,
    max_stdout_bytes: int,
    max_stderr_bytes: int,
    encoding: str,
    cancellation: CancellationToken,
    on_progress: ProgressCallback | None = None,
) -> ProcessCapture:
    """Execute ``command`` via the platform shell and capture structured output."""
    process_env = os.environ.copy()
    if env:
        process_env.update(env)

    started = perf_counter()
    try:
        process = _spawn(
            command,
            cwd=working_directory,
            env=process_env,
            encoding=encoding,
        )
    except OSError as exc:
        raise CapabilityExecutionError(
            f"Failed to start process: {exc}",
            code=PROCESS_FAILED,
            details={"os_error": type(exc).__name__},
        ) from exc

    collector = _OutputCollector(
        process,
        max_stdout_bytes=max_stdout_bytes,
        max_stderr_bytes=max_stderr_bytes,
    )
    collector.start()

    timed_out = False
    cancelled = False
    deadline = time.monotonic() + timeout_seconds
    last_progress = 0.0

    try:
        while process.poll() is None:
            if cancellation.is_cancelled:
                cancelled = True
                _terminate_process(process)
                break
            if time.monotonic() >= deadline:
                timed_out = True
                _terminate_process(process)
                break
            now = time.monotonic()
            if on_progress is not None and now - last_progress >= 0.2:
                on_progress(
                    {
                        "stdout": collector.stdout,
                        "stderr": collector.stderr,
                        "stdout_truncated": collector.stdout_truncated,
                        "stderr_truncated": collector.stderr_truncated,
                    }
                )
                last_progress = now
            time.sleep(0.05)

        exit_code = process.poll()
        if exit_code is None:
            _terminate_process(process)
            try:
                exit_code = process.wait(timeout=2.0)
            except subprocess.TimeoutExpired:
                exit_code = -1

        duration = perf_counter() - started
        # Close pipes so reader threads can finish, then join them.
        _close_streams(process)
        collector.join(timeout=2.0)

        if on_progress is not None:
            on_progress(
                {
                    "stdout": collector.stdout,
                    "stderr": collector.stderr,
                    "stdout_truncated": collector.stdout_truncated,
                    "stderr_truncated": collector.stderr_truncated,
                }
            )

        stdout_text = collector.stdout
        stderr_text = collector.stderr
        stdout_truncated = collector.stdout_truncated
        stderr_truncated = collector.stderr_truncated

        if cancelled:
            raise CapabilityCancelledError("Terminal command was cancelled.")
        if timed_out:
            raise CapabilityExecutionError(
                f"Terminal command timed out after {timeout_seconds} seconds.",
                code=TIMEOUT,
                details={
                    "timeout_seconds": timeout_seconds,
                    "command": command,
                    "working_directory": str(working_directory),
                    "stdout": stdout_text,
                    "stderr": stderr_text,
                },
            )

        return ProcessCapture(
            command=command,
            working_directory=str(working_directory),
            exit_code=exit_code,
            stdout=stdout_text,
            stderr=stderr_text,
            duration_seconds=duration,
            timed_out=False,
            cancelled=False,
            stdout_truncated=stdout_truncated,
            stderr_truncated=stderr_truncated,
        )
    finally:
        if process.poll() is None:
            _terminate_process(process)
        _close_streams(process)
        collector.join(timeout=1.0)


def _spawn(
    command: str,
    *,
    cwd: Path,
    env: dict[str, str],
    encoding: str,
) -> subprocess.Popen[str]:
    kwargs: dict[str, object] = {
        "args": command,
        "shell": True,
        "cwd": str(cwd),
        "env": env,
        "stdin": subprocess.DEVNULL,
        "stdout": subprocess.PIPE,
        "stderr": subprocess.PIPE,
        "text": True,
        "encoding": encoding,
        "errors": "replace",
    }
    if sys.platform == "win32":
        # New process group so we can terminate the whole tree on cancel/timeout.
        kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP  # type: ignore[attr-defined]
    else:
        kwargs["start_new_session"] = True
    return subprocess.Popen(**kwargs)  # type: ignore[arg-type]


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
            # /T kills the process tree started for the shell command.
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
            if sys.platform != "win32":
                os.killpg(process.pid, signal.SIGKILL)
            else:
                process.kill()
        except OSError:
            pass
        try:
            process.wait(timeout=1.0)
        except subprocess.TimeoutExpired:
            pass


class _OutputCollector:
    """Background stdout/stderr readers with byte caps."""

    def __init__(
        self,
        process: subprocess.Popen[str],
        *,
        max_stdout_bytes: int,
        max_stderr_bytes: int,
    ) -> None:
        self._process = process
        self._max_stdout = max_stdout_bytes
        self._max_stderr = max_stderr_bytes
        self._stdout_parts: list[str] = []
        self._stderr_parts: list[str] = []
        self._stdout_bytes = 0
        self._stderr_bytes = 0
        self.stdout_truncated = False
        self.stderr_truncated = False
        self._lock = threading.Lock()
        self._threads: list[threading.Thread] = []

    def start(self) -> None:
        if self._process.stdout is not None:
            thread = threading.Thread(
                target=self._read_stream,
                args=(self._process.stdout, True),
                name="terminal-stdout",
                daemon=True,
            )
            self._threads.append(thread)
            thread.start()
        if self._process.stderr is not None:
            thread = threading.Thread(
                target=self._read_stream,
                args=(self._process.stderr, False),
                name="terminal-stderr",
                daemon=True,
            )
            self._threads.append(thread)
            thread.start()

    def join(self, *, timeout: float) -> None:
        deadline = time.monotonic() + timeout
        for thread in self._threads:
            remaining = max(0.0, deadline - time.monotonic())
            thread.join(timeout=remaining)

    @property
    def stdout(self) -> str:
        with self._lock:
            return "".join(self._stdout_parts)

    @property
    def stderr(self) -> str:
        with self._lock:
            return "".join(self._stderr_parts)

    def _read_stream(self, stream: object, is_stdout: bool) -> None:
        read = getattr(stream, "read", None)
        if not callable(read):
            return
        # Read in chunks so large pipes do not block forever in one call.
        while True:
            try:
                chunk = read(4096)
            except (OSError, ValueError):
                break
            if not chunk:
                break
            text = chunk if isinstance(chunk, str) else str(chunk)
            encoded = text.encode("utf-8", errors="replace")
            with self._lock:
                if is_stdout:
                    self._append_stdout(text, len(encoded))
                else:
                    self._append_stderr(text, len(encoded))

    def _append_stdout(self, text: str, size: int) -> None:
        if self.stdout_truncated:
            return
        remaining = self._max_stdout - self._stdout_bytes
        if size <= remaining:
            self._stdout_parts.append(text)
            self._stdout_bytes += size
            return
        if remaining > 0:
            # Approximate truncation on character boundary after byte budget.
            clipped = text.encode("utf-8", errors="replace")[:remaining].decode(
                "utf-8",
                errors="replace",
            )
            self._stdout_parts.append(clipped)
            self._stdout_bytes = self._max_stdout
        self.stdout_truncated = True

    def _append_stderr(self, text: str, size: int) -> None:
        if self.stderr_truncated:
            return
        remaining = self._max_stderr - self._stderr_bytes
        if size <= remaining:
            self._stderr_parts.append(text)
            self._stderr_bytes += size
            return
        if remaining > 0:
            clipped = text.encode("utf-8", errors="replace")[:remaining].decode(
                "utf-8",
                errors="replace",
            )
            self._stderr_parts.append(clipped)
            self._stderr_bytes = self._max_stderr
        self.stderr_truncated = True
