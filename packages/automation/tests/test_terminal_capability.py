import sys
from pathlib import Path

import pytest
from memovi_automation import (
    TERMINAL_EXECUTE,
    CapabilityContext,
    CapabilityInvoker,
    CapabilityRegistry,
    CapabilityRequest,
    TerminalCapabilityConfig,
    register_terminal_capability,
)
from memovi_automation.terminal import CAPABILITY_ID, EMPTY_COMMAND, INVALID_WORKING_DIRECTORY
from memovi_shared import WorkspaceId


@pytest.fixture
def sandbox(tmp_path: Path) -> Path:
    root = tmp_path / "terminal-root"
    root.mkdir()
    (root / "marker.txt").write_text("present", encoding="utf-8")
    nested = root / "nested"
    nested.mkdir()
    return root


@pytest.fixture
def outside(tmp_path: Path) -> Path:
    path = tmp_path / "outside"
    path.mkdir()
    return path


def _stack(root: Path, **config_kwargs):
    registry = CapabilityRegistry()
    config = TerminalCapabilityConfig.from_roots([root], **config_kwargs)
    capability = register_terminal_capability(registry, config)
    return registry, CapabilityInvoker(registry=registry), capability


def _context(*, granted=frozenset({TERMINAL_EXECUTE})) -> CapabilityContext:
    return CapabilityContext.create(
        workspace_id=WorkspaceId.default(),
        granted_permissions=granted,
        correlation_id="terminal-test",
    )


def _invoke(
    invoker: CapabilityInvoker,
    *,
    command: str,
    working_directory: str | None = None,
    env: dict[str, str] | None = None,
    timeout_seconds: float | None = None,
    granted=frozenset({TERMINAL_EXECUTE}),
):
    arguments: dict[str, object] = {"command": command}
    if working_directory is not None:
        arguments["working_directory"] = working_directory
    if env is not None:
        arguments["env"] = env
    if timeout_seconds is not None:
        arguments["timeout_seconds"] = timeout_seconds
    return invoker.invoke(
        CapabilityRequest.create(capability_id=CAPABILITY_ID, arguments=arguments),
        _context(granted=granted),
    )


def _echo_command(message: str) -> str:
    if sys.platform == "win32":
        return f"echo {message}"
    return f"echo {message}"


def _pwd_command() -> str:
    if sys.platform == "win32":
        return "cd"
    return "pwd"


def _fail_command() -> str:
    if sys.platform == "win32":
        return "cmd /c exit 7"
    return "sh -c 'exit 7'"


def _sleep_command(seconds: float) -> str:
    if sys.platform == "win32":
        # ping waits roughly N seconds with -n N+1 on localhost.
        count = max(2, int(seconds) + 1)
        return f"ping -n {count} 127.0.0.1 >NUL"
    return f"sleep {seconds}"


def test_terminal_capability_is_discoverable(sandbox: Path) -> None:
    registry, _invoker, capability = _stack(sandbox)

    assert registry.contains(CAPABILITY_ID)
    metadata = registry.metadata(CAPABILITY_ID)
    assert metadata.id == "terminal"
    assert "terminal.execute" in metadata.permission_names()
    assert {parameter.name for parameter in metadata.parameters} >= {
        "command",
        "working_directory",
        "env",
        "timeout_seconds",
    }
    assert registry.get(CAPABILITY_ID) is capability


def test_execute_captures_stdout_stderr_exit_code_and_duration(sandbox: Path) -> None:
    _registry, invoker, _capability = _stack(sandbox)

    result = _invoke(invoker, command=_echo_command("hello-terminal"))

    assert result.success is True
    assert result.output is not None
    assert result.output["operation"] == "execute"
    assert result.output["success"] is True
    assert result.output["exit_code"] == 0
    assert "hello-terminal" in result.output["stdout"]
    assert isinstance(result.output["stderr"], str)
    assert result.output["duration_seconds"] >= 0
    assert Path(result.output["working_directory"]) == sandbox.resolve()


def test_execute_in_working_directory(sandbox: Path) -> None:
    _registry, invoker, _capability = _stack(sandbox)
    nested = sandbox / "nested"

    result = _invoke(
        invoker,
        command=_pwd_command(),
        working_directory=str(nested),
    )

    assert result.success is True
    assert result.output is not None
    assert Path(result.output["working_directory"]) == nested.resolve()
    assert (
        str(nested.resolve()) in result.output["stdout"].replace("/", "\\")
        or str(nested.resolve()) in result.output["stdout"]
    )


def test_non_zero_exit_is_completed_capability_with_success_false(sandbox: Path) -> None:
    _registry, invoker, _capability = _stack(sandbox)

    result = _invoke(invoker, command=_fail_command())

    assert result.success is True  # process ran; payload reports command failure
    assert result.output is not None
    assert result.output["exit_code"] == 7
    assert result.output["success"] is False


def test_empty_command_rejected(sandbox: Path) -> None:
    _registry, invoker, _capability = _stack(sandbox)

    result = _invoke(invoker, command="   ")

    assert result.success is False
    assert result.error is not None
    assert result.error.code == EMPTY_COMMAND


def test_invalid_working_directory_rejected(sandbox: Path, outside: Path) -> None:
    _registry, invoker, _capability = _stack(sandbox)

    missing = _invoke(
        invoker,
        command=_echo_command("x"),
        working_directory=str(sandbox / "missing-dir"),
    )
    assert missing.success is False
    assert missing.error is not None
    assert missing.error.code == INVALID_WORKING_DIRECTORY

    escaped = _invoke(
        invoker,
        command=_echo_command("x"),
        working_directory=str(outside),
    )
    assert escaped.success is False
    assert escaped.error is not None
    assert escaped.error.code == INVALID_WORKING_DIRECTORY


def test_permission_required(sandbox: Path) -> None:
    _registry, invoker, _capability = _stack(sandbox)

    result = _invoke(
        invoker,
        command=_echo_command("denied"),
        granted=frozenset(),
    )

    assert result.success is False
    assert result.error is not None
    assert result.error.code == "permission_denied"


def test_environment_variables_are_applied(sandbox: Path) -> None:
    _registry, invoker, _capability = _stack(sandbox)
    if sys.platform == "win32":
        command = "echo %MEMOVI_TERMINAL_TEST%"
    else:
        command = "echo $MEMOVI_TERMINAL_TEST"

    result = _invoke(
        invoker,
        command=command,
        env={"MEMOVI_TERMINAL_TEST": "env-ok"},
    )

    assert result.success is True
    assert result.output is not None
    assert "env-ok" in result.output["stdout"]


def test_timeout_terminates_process(sandbox: Path) -> None:
    _registry, invoker, _capability = _stack(
        sandbox,
        default_timeout_seconds=1.0,
        max_timeout_seconds=2.0,
    )

    result = _invoke(
        invoker,
        command=_sleep_command(20),
        timeout_seconds=0.5,
    )

    assert result.success is False
    assert result.error is not None
    assert result.error.code == "timeout"


def test_stdout_is_truncated_at_max_size(sandbox: Path) -> None:
    _registry, invoker, _capability = _stack(sandbox, max_stdout_bytes=32)
    if sys.platform == "win32":
        command = "python -c \"print('x'*200)\""
    else:
        command = "python3 -c \"print('x'*200)\""

    result = _invoke(invoker, command=command)

    # Python may be unavailable in some CI images; skip soft if launch fails.
    if not result.success and result.error and result.error.code == "process_failed":
        pytest.skip("python interpreter unavailable for truncation test")
    assert result.success is True
    assert result.output is not None
    assert result.output["stdout_truncated"] is True
    assert len(result.output["stdout"].encode("utf-8")) <= 32
