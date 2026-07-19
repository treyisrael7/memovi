from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from memovi_automation.domain.exceptions import InvalidCapabilityError


@dataclass(frozen=True, slots=True)
class FilesystemCapabilityConfig:
    """Configuration for the read-only Filesystem Capability.

    Access is restricted to ``allowed_roots``. Paths are normalized and must
    resolve under one of those roots. Write-oriented settings are intentionally
    absent so future write milestones can extend this config without breaking
    the read-only surface.
    """

    allowed_roots: tuple[Path, ...]
    max_read_bytes: int = 1_048_576
    default_encoding: str = "utf-8"

    def __post_init__(self) -> None:
        if not self.allowed_roots:
            raise InvalidCapabilityError(
                "FilesystemCapabilityConfig.allowed_roots must contain at least one root.",
            )
        if self.max_read_bytes <= 0:
            raise InvalidCapabilityError(
                "FilesystemCapabilityConfig.max_read_bytes must be positive.",
            )
        encoding = self.default_encoding.strip()
        if not encoding:
            raise InvalidCapabilityError(
                "FilesystemCapabilityConfig.default_encoding is required.",
            )

        normalized_roots: list[Path] = []
        for root in self.allowed_roots:
            if not isinstance(root, Path):
                raise InvalidCapabilityError(
                    "FilesystemCapabilityConfig.allowed_roots must contain Path instances.",
                )
            resolved = root.expanduser().resolve(strict=False)
            if not resolved.exists():
                raise InvalidCapabilityError(
                    f"Filesystem allowed root does not exist: {resolved}",
                )
            if not resolved.is_dir():
                raise InvalidCapabilityError(
                    f"Filesystem allowed root must be a directory: {resolved}",
                )
            normalized_roots.append(resolved)

        object.__setattr__(self, "allowed_roots", tuple(normalized_roots))
        object.__setattr__(self, "default_encoding", encoding)

    @classmethod
    def from_roots(
        cls,
        roots: Iterable[Path | str],
        *,
        max_read_bytes: int = 1_048_576,
        default_encoding: str = "utf-8",
    ) -> FilesystemCapabilityConfig:
        return cls(
            allowed_roots=tuple(Path(root) for root in roots),
            max_read_bytes=max_read_bytes,
            default_encoding=default_encoding,
        )
