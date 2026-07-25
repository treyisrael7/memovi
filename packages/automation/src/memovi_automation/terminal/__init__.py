"""Production Terminal Capability — structured OS command execution."""

from memovi_automation.terminal.capability import (
    CAPABILITY_ID,
    EXECUTE_OPERATION,
    TerminalCapability,
    register_terminal_capability,
)
from memovi_automation.terminal.config import TerminalCapabilityConfig
from memovi_automation.terminal.errors import (
    EMPTY_COMMAND,
    INVALID_ENVIRONMENT,
    INVALID_TIMEOUT,
    INVALID_WORKING_DIRECTORY,
    OUTPUT_TOO_LARGE,
    PERMISSION_DENIED,
    PROCESS_FAILED,
    TIMEOUT,
    UNSUPPORTED_OPERATION,
)

__all__ = [
    "CAPABILITY_ID",
    "EMPTY_COMMAND",
    "EXECUTE_OPERATION",
    "INVALID_ENVIRONMENT",
    "INVALID_TIMEOUT",
    "INVALID_WORKING_DIRECTORY",
    "OUTPUT_TOO_LARGE",
    "PERMISSION_DENIED",
    "PROCESS_FAILED",
    "TIMEOUT",
    "UNSUPPORTED_OPERATION",
    "TerminalCapability",
    "TerminalCapabilityConfig",
    "register_terminal_capability",
]
