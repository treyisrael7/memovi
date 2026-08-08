from __future__ import annotations

import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from pathlib import Path

from memovi_automation.domain.exceptions import (
    CapabilityExecutionError,
    InvalidCapabilityError,
)
from memovi_automation.terminal.command_policy import (
    compile_denied_argument_patterns,
    default_confirmation_required_executables,
    default_denied_argument_patterns,
    default_denied_executables,
)


@dataclass(frozen=True, slots=True)
class TerminalCapabilityConfig:
    """Configuration for the Terminal Capability.

    Working directories are restricted to ``allowed_roots``. Timeouts and output
    caps bound process execution so callers cannot request unbounded work.
    Command policy lists are evaluated before any process starts.
    """

    allowed_roots: tuple[Path, ...]
    default_timeout_seconds: float = 30.0
    max_timeout_seconds: float = 300.0
    max_stdout_bytes: int = 1_048_576
    max_stderr_bytes: int = 1_048_576
    default_encoding: str = "utf-8"
    # None = no allow-list restriction (deny/confirm lists still apply).
    allowed_executables: frozenset[str] | None = None
    denied_executables: frozenset[str] = field(
        default_factory=default_denied_executables,
    )
    confirmation_required_executables: frozenset[str] = field(
        default_factory=default_confirmation_required_executables,
    )
    denied_argument_patterns: tuple[str, ...] = field(
        default_factory=default_denied_argument_patterns,
    )
    prefer_argv: bool = True
    allow_shell: bool = True

    def __post_init__(self) -> None:
        if not self.allowed_roots:
            raise InvalidCapabilityError(
                "TerminalCapabilityConfig.allowed_roots must contain at least one root.",
            )
        if self.default_timeout_seconds <= 0:
            raise InvalidCapabilityError(
                "TerminalCapabilityConfig.default_timeout_seconds must be positive.",
            )
        if self.max_timeout_seconds <= 0:
            raise InvalidCapabilityError(
                "TerminalCapabilityConfig.max_timeout_seconds must be positive.",
            )
        if self.default_timeout_seconds > self.max_timeout_seconds:
            raise InvalidCapabilityError(
                "TerminalCapabilityConfig.default_timeout_seconds cannot exceed "
                "max_timeout_seconds.",
            )
        if self.max_stdout_bytes <= 0:
            raise InvalidCapabilityError(
                "TerminalCapabilityConfig.max_stdout_bytes must be positive.",
            )
        if self.max_stderr_bytes <= 0:
            raise InvalidCapabilityError(
                "TerminalCapabilityConfig.max_stderr_bytes must be positive.",
            )
        encoding = self.default_encoding.strip()
        if not encoding:
            raise InvalidCapabilityError(
                "TerminalCapabilityConfig.default_encoding is required.",
            )
        if not self.prefer_argv and not self.allow_shell:
            raise InvalidCapabilityError(
                "TerminalCapabilityConfig requires prefer_argv and/or allow_shell.",
            )

        normalized_roots: list[Path] = []
        for root in self.allowed_roots:
            if not isinstance(root, Path):
                raise InvalidCapabilityError(
                    "TerminalCapabilityConfig.allowed_roots must contain Path instances.",
                )
            resolved = root.expanduser().resolve(strict=False)
            if not resolved.exists():
                raise InvalidCapabilityError(
                    f"Terminal allowed root does not exist: {resolved}",
                )
            if not resolved.is_dir():
                raise InvalidCapabilityError(
                    f"Terminal allowed root must be a directory: {resolved}",
                )
            normalized_roots.append(resolved)

        allowed = None
        if self.allowed_executables is not None:
            allowed = frozenset(
                item.strip().lower()
                for item in self.allowed_executables
                if str(item).strip()
            )
        denied = frozenset(
            item.strip().lower() for item in self.denied_executables if str(item).strip()
        )
        confirm = frozenset(
            item.strip().lower()
            for item in self.confirmation_required_executables
            if str(item).strip()
        )
        patterns = tuple(
            pattern.strip()
            for pattern in self.denied_argument_patterns
            if str(pattern).strip()
        )
        try:
            compile_denied_argument_patterns(patterns)
        except CapabilityExecutionError as exc:
            raise InvalidCapabilityError(str(exc)) from exc

        object.__setattr__(self, "allowed_roots", tuple(normalized_roots))
        object.__setattr__(self, "default_encoding", encoding)
        object.__setattr__(self, "allowed_executables", allowed)
        object.__setattr__(self, "denied_executables", denied)
        object.__setattr__(self, "confirmation_required_executables", confirm)
        object.__setattr__(self, "denied_argument_patterns", patterns)

    def compiled_denied_argument_patterns(self) -> tuple[re.Pattern[str], ...]:
        return compile_denied_argument_patterns(self.denied_argument_patterns)

    @property
    def default_working_directory(self) -> Path:
        return self.allowed_roots[0]

    @classmethod
    def from_roots(
        cls,
        roots: Iterable[Path | str],
        *,
        default_timeout_seconds: float = 30.0,
        max_timeout_seconds: float = 300.0,
        max_stdout_bytes: int = 1_048_576,
        max_stderr_bytes: int = 1_048_576,
        default_encoding: str = "utf-8",
        allowed_executables: Iterable[str] | None = None,
        denied_executables: Iterable[str] | None = None,
        confirmation_required_executables: Iterable[str] | None = None,
        denied_argument_patterns: Sequence[str] | None = None,
        prefer_argv: bool = True,
        allow_shell: bool = True,
    ) -> TerminalCapabilityConfig:
        return cls(
            allowed_roots=tuple(Path(root) for root in roots),
            default_timeout_seconds=default_timeout_seconds,
            max_timeout_seconds=max_timeout_seconds,
            max_stdout_bytes=max_stdout_bytes,
            max_stderr_bytes=max_stderr_bytes,
            default_encoding=default_encoding,
            allowed_executables=(
                None if allowed_executables is None else frozenset(allowed_executables)
            ),
            denied_executables=(
                default_denied_executables()
                if denied_executables is None
                else frozenset(denied_executables)
            ),
            confirmation_required_executables=(
                default_confirmation_required_executables()
                if confirmation_required_executables is None
                else frozenset(confirmation_required_executables)
            ),
            denied_argument_patterns=(
                default_denied_argument_patterns()
                if denied_argument_patterns is None
                else tuple(denied_argument_patterns)
            ),
            prefer_argv=prefer_argv,
            allow_shell=allow_shell,
        )
