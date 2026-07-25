from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from memovi_automation.domain.exceptions import InvalidCapabilityError


@dataclass(frozen=True, slots=True)
class TerminalCapabilityConfig:
    """Configuration for the Terminal Capability.

    Working directories are restricted to ``allowed_roots``. Timeouts and output
    caps bound process execution so callers cannot request unbounded work.
    """

    allowed_roots: tuple[Path, ...]
    default_timeout_seconds: float = 30.0
    max_timeout_seconds: float = 300.0
    max_stdout_bytes: int = 1_048_576
    max_stderr_bytes: int = 1_048_576
    default_encoding: str = "utf-8"

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

        object.__setattr__(self, "allowed_roots", tuple(normalized_roots))
        object.__setattr__(self, "default_encoding", encoding)

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
    ) -> TerminalCapabilityConfig:
        return cls(
            allowed_roots=tuple(Path(root) for root in roots),
            default_timeout_seconds=default_timeout_seconds,
            max_timeout_seconds=max_timeout_seconds,
            max_stdout_bytes=max_stdout_bytes,
            max_stderr_bytes=max_stderr_bytes,
            default_encoding=default_encoding,
        )
