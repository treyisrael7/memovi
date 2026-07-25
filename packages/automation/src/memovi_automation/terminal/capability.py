from collections.abc import Callable, Mapping
from typing import Final

from memovi_automation.application.services.capability_registry import CapabilityRegistry
from memovi_automation.domain.exceptions import CapabilityExecutionError
from memovi_automation.domain.value_objects import (
    TERMINAL_EXECUTE,
    CapabilityContext,
    CapabilityMetadata,
    CapabilityParameter,
    CapabilityPermission,
    CapabilityRequest,
)
from memovi_automation.terminal.config import TerminalCapabilityConfig
from memovi_automation.terminal.cwd_safety import resolve_working_directory
from memovi_automation.terminal.errors import (
    EMPTY_COMMAND,
    INVALID_ENVIRONMENT,
    INVALID_TIMEOUT,
    PERMISSION_DENIED,
    UNSUPPORTED_OPERATION,
)
from memovi_automation.terminal.runner import run_command

CAPABILITY_ID: Final = "terminal"

EXECUTE_OPERATION: Final = "execute"

_TERMINAL_PERMISSIONS: Final[tuple[CapabilityPermission, ...]] = (TERMINAL_EXECUTE,)


class TerminalCapability:
    """Trusted terminal capability — structured OS command execution.

    Discoverable through ``CapabilityRegistry`` under id ``terminal``.
    Commands run only when invoked; the Capability Execution Engine owns
    approval, permission modes, and audit. This capability never exposes raw
    process objects and must not be called directly by LLM tool loops.
    """

    def __init__(self, config: TerminalCapabilityConfig) -> None:
        self._config = config

    @property
    def config(self) -> TerminalCapabilityConfig:
        return self._config

    def supported_operations(self) -> frozenset[str]:
        return frozenset({EXECUTE_OPERATION})

    def metadata(self) -> CapabilityMetadata:
        return CapabilityMetadata(
            id=CAPABILITY_ID,
            description=(
                "Root-scoped terminal command execution with captured stdout, "
                "stderr, exit code, and duration. Supports working directory, "
                "environment variables, timeouts, and cancellation."
            ),
            permissions=_TERMINAL_PERMISSIONS,
            parameters=(
                CapabilityParameter(
                    name="operation",
                    type="string",
                    description="Terminal operation name (currently: execute).",
                    required=False,
                ),
                CapabilityParameter(
                    name="command",
                    type="string",
                    description="Shell command to execute (for example: git status).",
                ),
                CapabilityParameter(
                    name="working_directory",
                    type="string",
                    description=(
                        "Working directory under an allowed root. Defaults to the "
                        "first allowed root when omitted."
                    ),
                    required=False,
                ),
                CapabilityParameter(
                    name="env",
                    type="object",
                    description=(
                        "Additional environment variables merged into the process "
                        "environment. Sensitive keys are redacted in audit logs."
                    ),
                    required=False,
                ),
                CapabilityParameter(
                    name="timeout_seconds",
                    type="number",
                    description=(
                        "Execution timeout in seconds (capped by capability "
                        "max_timeout_seconds)."
                    ),
                    required=False,
                ),
            ),
        )

    def execute(self, request: CapabilityRequest, context: CapabilityContext) -> object:
        context.check_cancelled()

        if not context.has_permission(TERMINAL_EXECUTE):
            raise CapabilityExecutionError(
                f"Missing required permission '{TERMINAL_EXECUTE}'.",
                code=PERMISSION_DENIED,
                details={"permission": TERMINAL_EXECUTE.name},
            )

        operation = _optional_operation(request.arguments)
        if operation != EXECUTE_OPERATION:
            raise CapabilityExecutionError(
                f"Unsupported terminal operation '{operation}'.",
                code=UNSUPPORTED_OPERATION,
                details={"operation": operation},
            )

        command = _require_command(request.arguments)
        working_directory = resolve_working_directory(
            request.arguments.get("working_directory"),
            allowed_roots=self._config.allowed_roots,
            default=self._config.default_working_directory,
        )
        env = _optional_env(request.arguments)
        timeout_seconds = _resolve_timeout(request.arguments, self._config)
        on_progress = _progress_callback(context)

        context.check_cancelled()
        capture = run_command(
            command,
            working_directory=working_directory,
            env=env,
            timeout_seconds=timeout_seconds,
            max_stdout_bytes=self._config.max_stdout_bytes,
            max_stderr_bytes=self._config.max_stderr_bytes,
            encoding=self._config.default_encoding,
            cancellation=context.cancellation,
            on_progress=on_progress,
        )

        exit_code = 0 if capture.exit_code is None else capture.exit_code
        success = exit_code == 0
        return {
            "operation": EXECUTE_OPERATION,
            "command": capture.command,
            "working_directory": capture.working_directory,
            "exit_code": exit_code,
            "stdout": capture.stdout,
            "stderr": capture.stderr,
            "duration_seconds": capture.duration_seconds,
            "success": success,
            "cancelled": False,
            "timed_out": False,
            "stdout_truncated": capture.stdout_truncated,
            "stderr_truncated": capture.stderr_truncated,
            "metadata": {
                "exit_code": exit_code,
                "duration_seconds": capture.duration_seconds,
                "timeout_seconds": timeout_seconds,
                "stdout_truncated": capture.stdout_truncated,
                "stderr_truncated": capture.stderr_truncated,
            },
        }


def register_terminal_capability(
    registry: CapabilityRegistry,
    config: TerminalCapabilityConfig,
) -> TerminalCapability:
    """Register the Terminal Capability on a CapabilityRegistry."""
    capability = TerminalCapability(config)
    registry.register(capability)
    return capability


def _optional_operation(arguments: Mapping[str, object]) -> str:
    value = arguments.get("operation", EXECUTE_OPERATION)
    if not isinstance(value, str) or not value.strip():
        raise CapabilityExecutionError(
            "Argument 'operation' must be a non-empty string when provided.",
            code=UNSUPPORTED_OPERATION,
            details={"argument": "operation"},
        )
    return value.strip()


def _require_command(arguments: Mapping[str, object]) -> str:
    value = arguments.get("command")
    if not isinstance(value, str) or not value.strip():
        raise CapabilityExecutionError(
            "Argument 'command' must be a non-empty string.",
            code=EMPTY_COMMAND,
            details={"argument": "command"},
        )
    return value.strip()


def _optional_env(arguments: Mapping[str, object]) -> dict[str, str] | None:
    if "env" not in arguments:
        return None
    value = arguments["env"]
    if not isinstance(value, Mapping):
        raise CapabilityExecutionError(
            "Argument 'env' must be an object of string keys and string values.",
            code=INVALID_ENVIRONMENT,
            details={"argument": "env"},
        )
    normalized: dict[str, str] = {}
    for key, item in value.items():
        if not isinstance(key, str) or not key.strip():
            raise CapabilityExecutionError(
                "Environment variable names must be non-empty strings.",
                code=INVALID_ENVIRONMENT,
                details={"argument": "env"},
            )
        if not isinstance(item, str):
            raise CapabilityExecutionError(
                "Environment variable values must be strings.",
                code=INVALID_ENVIRONMENT,
                details={"argument": "env", "key": key},
            )
        normalized[key] = item
    return normalized


def _resolve_timeout(
    arguments: Mapping[str, object],
    config: TerminalCapabilityConfig,
) -> float:
    if "timeout_seconds" not in arguments:
        return config.default_timeout_seconds
    value = arguments["timeout_seconds"]
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise CapabilityExecutionError(
            "Argument 'timeout_seconds' must be a positive number.",
            code=INVALID_TIMEOUT,
            details={"argument": "timeout_seconds"},
        )
    timeout = float(value)
    if timeout <= 0:
        raise CapabilityExecutionError(
            "Argument 'timeout_seconds' must be a positive number.",
            code=INVALID_TIMEOUT,
            details={"argument": "timeout_seconds", "timeout_seconds": timeout},
        )
    return min(timeout, config.max_timeout_seconds)


def _progress_callback(context: CapabilityContext) -> Callable[[Mapping[str, object]], None] | None:
    reporter = context.metadata.get("report_progress")
    if not callable(reporter):
        return None

    def _report(partial: Mapping[str, object]) -> None:
        try:
            reporter(
                {
                    "operation": EXECUTE_OPERATION,
                    "stdout": partial.get("stdout", ""),
                    "stderr": partial.get("stderr", ""),
                    "stdout_truncated": bool(partial.get("stdout_truncated")),
                    "stderr_truncated": bool(partial.get("stderr_truncated")),
                    "success": False,
                    "streaming": True,
                    "metadata": {"streaming": True},
                }
            )
        except Exception:
            # Progress is best-effort; never fail the command because of UI updates.
            return

    return _report
