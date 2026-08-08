"""Production Terminal Capability — structured OS command execution."""

from memovi_automation.terminal.capability import (
    CAPABILITY_ID,
    EXECUTE_OPERATION,
    TerminalCapability,
    register_terminal_capability,
)
from memovi_automation.terminal.command_policy import (
    CommandPolicyDecision,
    CommandPolicyEffect,
    evaluate_command_policy,
    parse_command,
    redact_command_for_audit,
)
from memovi_automation.terminal.config import TerminalCapabilityConfig
from memovi_automation.terminal.errors import (
    COMMAND_DENIED,
    EMPTY_COMMAND,
    INVALID_ARGUMENTS,
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
    "COMMAND_DENIED",
    "EMPTY_COMMAND",
    "EXECUTE_OPERATION",
    "INVALID_ARGUMENTS",
    "INVALID_ENVIRONMENT",
    "INVALID_TIMEOUT",
    "INVALID_WORKING_DIRECTORY",
    "OUTPUT_TOO_LARGE",
    "PERMISSION_DENIED",
    "PROCESS_FAILED",
    "TIMEOUT",
    "UNSUPPORTED_OPERATION",
    "CommandPolicyDecision",
    "CommandPolicyEffect",
    "TerminalCapability",
    "TerminalCapabilityConfig",
    "evaluate_command_policy",
    "parse_command",
    "redact_command_for_audit",
    "register_terminal_capability",
]
