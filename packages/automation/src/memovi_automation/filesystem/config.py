from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from memovi_automation.domain.exceptions import InvalidCapabilityError

_VALID_OVERWRITE_POLICIES = frozenset({"reject", "ask_user", "replace"})
_VALID_DELETE_MODES = frozenset({"trash", "permanent"})


@dataclass(frozen=True, slots=True)
class FilesystemCapabilityConfig:
    """Configuration for the Filesystem Capability.

    Access is restricted to ``allowed_roots``. Paths are normalized and must
    resolve under one of those roots. Write settings control size limits and
    default overwrite / deletion policies without changing read defaults.
    """

    allowed_roots: tuple[Path, ...]
    max_read_bytes: int = 1_048_576
    max_write_bytes: int = 1_048_576
    default_encoding: str = "utf-8"
    default_overwrite_policy: str = "reject"
    default_delete_mode: str = "trash"
    allow_permanent_delete: bool = True

    def __post_init__(self) -> None:
        if not self.allowed_roots:
            raise InvalidCapabilityError(
                "FilesystemCapabilityConfig.allowed_roots must contain at least one root.",
            )
        if self.max_read_bytes <= 0:
            raise InvalidCapabilityError(
                "FilesystemCapabilityConfig.max_read_bytes must be positive.",
            )
        if self.max_write_bytes <= 0:
            raise InvalidCapabilityError(
                "FilesystemCapabilityConfig.max_write_bytes must be positive.",
            )
        encoding = self.default_encoding.strip()
        if not encoding:
            raise InvalidCapabilityError(
                "FilesystemCapabilityConfig.default_encoding is required.",
            )
        overwrite = self.default_overwrite_policy.strip().lower()
        if overwrite not in _VALID_OVERWRITE_POLICIES:
            raise InvalidCapabilityError(
                "FilesystemCapabilityConfig.default_overwrite_policy must be "
                "reject, ask_user, or replace.",
            )
        delete_mode = self.default_delete_mode.strip().lower()
        if delete_mode not in _VALID_DELETE_MODES:
            raise InvalidCapabilityError(
                "FilesystemCapabilityConfig.default_delete_mode must be trash or permanent.",
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
        object.__setattr__(self, "default_overwrite_policy", overwrite)
        object.__setattr__(self, "default_delete_mode", delete_mode)

    @classmethod
    def from_roots(
        cls,
        roots: Iterable[Path | str],
        *,
        max_read_bytes: int = 1_048_576,
        max_write_bytes: int = 1_048_576,
        default_encoding: str = "utf-8",
        default_overwrite_policy: str = "reject",
        default_delete_mode: str = "trash",
        allow_permanent_delete: bool = True,
    ) -> FilesystemCapabilityConfig:
        return cls(
            allowed_roots=tuple(Path(root) for root in roots),
            max_read_bytes=max_read_bytes,
            max_write_bytes=max_write_bytes,
            default_encoding=default_encoding,
            default_overwrite_policy=default_overwrite_policy,
            default_delete_mode=default_delete_mode,
            allow_permanent_delete=allow_permanent_delete,
        )
