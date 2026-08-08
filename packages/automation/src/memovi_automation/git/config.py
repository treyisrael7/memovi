from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from memovi_automation.domain.exceptions import InvalidCapabilityError


@dataclass(frozen=True, slots=True)
class GitCapabilityConfig:
    """Configuration for the Git Capability.

    Repository paths are restricted to ``allowed_roots``. Timeouts and output
    caps bound CLI execution so callers cannot request unbounded work.
    """

    allowed_roots: tuple[Path, ...]
    default_timeout_seconds: float = 60.0
    max_timeout_seconds: float = 600.0
    max_diff_bytes: int = 1_048_576
    default_history_limit: int = 20
    max_history_limit: int = 200
    git_executable: str = "git"

    def __post_init__(self) -> None:
        if not self.allowed_roots:
            raise InvalidCapabilityError(
                "GitCapabilityConfig.allowed_roots must contain at least one root.",
            )
        if self.default_timeout_seconds <= 0:
            raise InvalidCapabilityError(
                "GitCapabilityConfig.default_timeout_seconds must be positive.",
            )
        if self.max_timeout_seconds <= 0:
            raise InvalidCapabilityError(
                "GitCapabilityConfig.max_timeout_seconds must be positive.",
            )
        if self.default_timeout_seconds > self.max_timeout_seconds:
            raise InvalidCapabilityError(
                "GitCapabilityConfig.default_timeout_seconds cannot exceed " "max_timeout_seconds.",
            )
        if self.max_diff_bytes <= 0:
            raise InvalidCapabilityError(
                "GitCapabilityConfig.max_diff_bytes must be positive.",
            )
        if self.default_history_limit <= 0:
            raise InvalidCapabilityError(
                "GitCapabilityConfig.default_history_limit must be positive.",
            )
        if self.max_history_limit <= 0:
            raise InvalidCapabilityError(
                "GitCapabilityConfig.max_history_limit must be positive.",
            )
        executable = self.git_executable.strip()
        if not executable:
            raise InvalidCapabilityError(
                "GitCapabilityConfig.git_executable is required.",
            )

        normalized_roots: list[Path] = []
        for root in self.allowed_roots:
            if not isinstance(root, Path):
                raise InvalidCapabilityError(
                    "GitCapabilityConfig.allowed_roots must contain Path instances.",
                )
            resolved = root.expanduser().resolve(strict=False)
            if not resolved.exists():
                raise InvalidCapabilityError(
                    f"Git allowed root does not exist: {resolved}",
                )
            if not resolved.is_dir():
                raise InvalidCapabilityError(
                    f"Git allowed root must be a directory: {resolved}",
                )
            normalized_roots.append(resolved)

        object.__setattr__(self, "allowed_roots", tuple(normalized_roots))
        object.__setattr__(self, "git_executable", executable)

    @classmethod
    def from_roots(
        cls,
        roots: Iterable[Path | str],
        *,
        default_timeout_seconds: float = 60.0,
        max_timeout_seconds: float = 600.0,
        max_diff_bytes: int = 1_048_576,
        default_history_limit: int = 20,
        max_history_limit: int = 200,
        git_executable: str = "git",
    ) -> GitCapabilityConfig:
        return cls(
            allowed_roots=tuple(Path(root) for root in roots),
            default_timeout_seconds=default_timeout_seconds,
            max_timeout_seconds=max_timeout_seconds,
            max_diff_bytes=max_diff_bytes,
            default_history_limit=default_history_limit,
            max_history_limit=max_history_limit,
            git_executable=git_executable,
        )
