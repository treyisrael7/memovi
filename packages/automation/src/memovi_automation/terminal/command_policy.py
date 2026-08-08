"""Terminal command parsing and execution-policy evaluation.

Evaluates allow/deny/confirmation rules against a parsed executable and
arguments before any process is started.
"""

from __future__ import annotations

import re
import shlex
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from memovi_automation.domain.exceptions import CapabilityExecutionError
from memovi_automation.terminal.errors import (
    COMMAND_DENIED,
    EMPTY_COMMAND,
    INVALID_ARGUMENTS,
)

# Destructive / privileged names that require confirmation by default.
_DEFAULT_CONFIRM_EXECUTABLES: frozenset[str] = frozenset(
    {
        "rm",
        "rmdir",
        "del",
        "erase",
        "rd",
        "sudo",
        "su",
        "chmod",
        "chown",
        "chgrp",
        "mkfs",
        "diskpart",
        "format",
        "shutdown",
        "reboot",
        "poweroff",
        "halt",
        "reg",
        "regedit",
        "schtasks",
        "launchctl",
        "systemctl",
        "service",
        "iptables",
        "ufw",
        "firewall-cmd",
    }
)

# Extremely high-risk names denied by default (can be overridden via config).
_DEFAULT_DENIED_EXECUTABLES: frozenset[str] = frozenset(
    {
        "mkfs",
        "diskpart",
        "format",
        "dd",
    }
)

_DEFAULT_DENIED_ARGUMENT_PATTERNS: tuple[str, ...] = (
    r"(?i)--password(=|$)",
    r"(?i)--passwd(=|$)",
    r"(?i)\bpassword=",
    r"(?i)\btoken=",
    r"(?i)\bapi[_-]?key=",
)

_SHELL_METACHAR_RE = re.compile(r"[|&;<>`$(){}\n]|\s&&\s|\s\|\|\s")


class CommandPolicyEffect(StrEnum):
    ALLOW = "allow"
    DENY = "deny"
    REQUIRE_CONFIRMATION = "require_confirmation"


@dataclass(frozen=True, slots=True)
class ParsedCommand:
    """Structured view of a command string."""

    raw: str
    executable: str
    executable_basename: str
    arguments: tuple[str, ...]
    argv: tuple[str, ...]
    needs_shell: bool


@dataclass(frozen=True, slots=True)
class CommandPolicyDecision:
    """Outcome of evaluating terminal command policy."""

    effect: CommandPolicyEffect
    executable: str
    reason: str
    code: str | None = None
    details: Mapping[str, object] | None = None

    def to_audit_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "effect": self.effect.value,
            "executable": self.executable,
            "reason": self.reason,
        }
        if self.code is not None:
            payload["code"] = self.code
        return payload


def parse_command(command: str) -> ParsedCommand:
    """Parse a command string into executable + arguments.

    Uses ``shlex`` so callers can prefer argv-based execution when practical.
    Raises ``CapabilityExecutionError`` for empty or unparseable commands.
    """
    if not isinstance(command, str) or not command.strip():
        raise CapabilityExecutionError(
            "Argument 'command' must be a non-empty string.",
            code=EMPTY_COMMAND,
            details={"argument": "command"},
        )
    raw = command.strip()
    if "\x00" in raw:
        raise CapabilityExecutionError(
            "Command contains a null byte.",
            code=INVALID_ARGUMENTS,
            details={"argument": "command"},
        )

    posix = sys.platform != "win32"
    try:
        tokens = shlex.split(raw, posix=posix)
    except ValueError as exc:
        raise CapabilityExecutionError(
            f"Command could not be parsed: {exc}",
            code=INVALID_ARGUMENTS,
            details={"argument": "command"},
        ) from exc

    if not tokens:
        raise CapabilityExecutionError(
            "Argument 'command' must be a non-empty string.",
            code=EMPTY_COMMAND,
            details={"argument": "command"},
        )

    executable = tokens[0]
    basename = _executable_basename(executable)
    needs_shell = bool(_SHELL_METACHAR_RE.search(raw))
    return ParsedCommand(
        raw=raw,
        executable=executable,
        executable_basename=basename,
        arguments=tuple(tokens[1:]),
        argv=tuple(tokens),
        needs_shell=needs_shell,
    )


def evaluate_command_policy(
    parsed: ParsedCommand,
    *,
    allowed_executables: frozenset[str] | None,
    denied_executables: frozenset[str],
    confirmation_required_executables: frozenset[str],
    denied_argument_patterns: Sequence[re.Pattern[str]],
) -> CommandPolicyDecision:
    """Evaluate allow/deny/confirmation rules for a parsed command."""
    name = parsed.executable_basename.lower()

    if name in {item.lower() for item in denied_executables}:
        return CommandPolicyDecision(
            effect=CommandPolicyEffect.DENY,
            executable=parsed.executable_basename,
            reason=f"Executable '{parsed.executable_basename}' is denied by policy.",
            code=COMMAND_DENIED,
            details={
                "executable": parsed.executable_basename,
                "policy": "deny_list",
            },
        )

    if allowed_executables is not None:
        allowed = {item.lower() for item in allowed_executables}
        if name not in allowed:
            return CommandPolicyDecision(
                effect=CommandPolicyEffect.DENY,
                executable=parsed.executable_basename,
                reason=(
                    f"Executable '{parsed.executable_basename}' is not on the "
                    "allow list."
                ),
                code=COMMAND_DENIED,
                details={
                    "executable": parsed.executable_basename,
                    "policy": "allow_list",
                },
            )

    for pattern in denied_argument_patterns:
        for argument in parsed.arguments:
            if pattern.search(argument):
                return CommandPolicyDecision(
                    effect=CommandPolicyEffect.DENY,
                    executable=parsed.executable_basename,
                    reason="Command arguments match a denied pattern.",
                    code=COMMAND_DENIED,
                    details={
                        "executable": parsed.executable_basename,
                        "policy": "denied_argument_pattern",
                        "pattern": pattern.pattern,
                    },
                )
        # Also scan the raw command for patterns that span tokens.
        if pattern.search(parsed.raw):
            return CommandPolicyDecision(
                effect=CommandPolicyEffect.DENY,
                executable=parsed.executable_basename,
                reason="Command matches a denied argument pattern.",
                code=COMMAND_DENIED,
                details={
                    "executable": parsed.executable_basename,
                    "policy": "denied_argument_pattern",
                    "pattern": pattern.pattern,
                },
            )

    confirm = {item.lower() for item in confirmation_required_executables}
    if name in confirm:
        return CommandPolicyDecision(
            effect=CommandPolicyEffect.REQUIRE_CONFIRMATION,
            executable=parsed.executable_basename,
            reason=(
                f"Executable '{parsed.executable_basename}' requires explicit "
                "approval."
            ),
            details={
                "executable": parsed.executable_basename,
                "policy": "confirmation_required",
            },
        )

    return CommandPolicyDecision(
        effect=CommandPolicyEffect.ALLOW,
        executable=parsed.executable_basename,
        reason="Command allowed by policy.",
        details={"executable": parsed.executable_basename, "policy": "allow"},
    )


def compile_denied_argument_patterns(
    patterns: Sequence[str],
) -> tuple[re.Pattern[str], ...]:
    compiled: list[re.Pattern[str]] = []
    for pattern in patterns:
        text = pattern.strip()
        if not text:
            continue
        try:
            compiled.append(re.compile(text))
        except re.error as exc:
            raise CapabilityExecutionError(
                f"Invalid denied argument pattern: {exc}",
                code=INVALID_ARGUMENTS,
                details={"pattern": text},
            ) from exc
    return tuple(compiled)


def default_denied_executables() -> frozenset[str]:
    return _DEFAULT_DENIED_EXECUTABLES


def default_confirmation_required_executables() -> frozenset[str]:
    return _DEFAULT_CONFIRM_EXECUTABLES


def default_denied_argument_patterns() -> tuple[str, ...]:
    return _DEFAULT_DENIED_ARGUMENT_PATTERNS


def redact_command_for_audit(command: str) -> str:
    """Redact likely secrets in command strings for audit/UI summaries."""
    redacted = command
    replacements = (
        (re.compile(r"(?i)(--password=)\S+"), r"\1[REDACTED]"),
        (re.compile(r"(?i)(--passwd=)\S+"), r"\1[REDACTED]"),
        (re.compile(r"(?i)(--token=)\S+"), r"\1[REDACTED]"),
        (re.compile(r"(?i)(--api[_-]?key=)\S+"), r"\1[REDACTED]"),
        (re.compile(r"(?i)\b(password=)\S+"), r"\1[REDACTED]"),
        (re.compile(r"(?i)\b(token=)\S+"), r"\1[REDACTED]"),
        (re.compile(r"(?i)\b(api[_-]?key=)\S+"), r"\1[REDACTED]"),
    )
    for pattern, repl in replacements:
        redacted = pattern.sub(repl, redacted)
    return redacted


def _executable_basename(executable: str) -> str:
    name = Path(executable).name
    if sys.platform == "win32" and name.lower().endswith((".exe", ".bat", ".cmd", ".com")):
        name = name.rsplit(".", 1)[0]
    return name
