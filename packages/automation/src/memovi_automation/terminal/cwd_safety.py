from pathlib import Path

from memovi_automation.domain.exceptions import CapabilityExecutionError
from memovi_automation.filesystem.path_safety import looks_like_windows_absolute
from memovi_automation.terminal.errors import INVALID_WORKING_DIRECTORY


def resolve_working_directory(
    raw_path: object | None,
    *,
    allowed_roots: tuple[Path, ...],
    default: Path,
) -> Path:
    """Resolve and validate a working directory under allowed roots.

    When ``raw_path`` is omitted, ``default`` is used (must already be an allowed root).
    Rejects blank paths, null bytes, traversal escapes, missing paths, and non-directories.
    """
    if raw_path is None:
        return default

    if not isinstance(raw_path, str):
        raise CapabilityExecutionError(
            "Working directory must be a string.",
            code=INVALID_WORKING_DIRECTORY,
            details={"path_type": type(raw_path).__name__},
        )

    path_text = raw_path.strip()
    if not path_text:
        raise CapabilityExecutionError(
            "Working directory cannot be blank.",
            code=INVALID_WORKING_DIRECTORY,
        )
    if "\x00" in path_text:
        raise CapabilityExecutionError(
            "Working directory contains a null byte.",
            code=INVALID_WORKING_DIRECTORY,
            details={"path": path_text},
        )

    candidate = Path(path_text)
    if candidate.is_absolute() or looks_like_windows_absolute(path_text):
        if not candidate.is_absolute():
            raise CapabilityExecutionError(
                "Working directory is outside allowed roots.",
                code=INVALID_WORKING_DIRECTORY,
                details={"path": path_text},
            )
        resolved = candidate.resolve(strict=False)
        if _matching_root(resolved, allowed_roots) is None:
            raise CapabilityExecutionError(
                "Working directory is outside allowed roots.",
                code=INVALID_WORKING_DIRECTORY,
                details={"path": path_text},
            )
    else:
        resolved_relative: Path | None = None
        for root in allowed_roots:
            candidate_resolved = (root / candidate).resolve(strict=False)
            if _is_within_root(candidate_resolved, root):
                resolved_relative = candidate_resolved
                break
        if resolved_relative is None:
            raise CapabilityExecutionError(
                "Working directory is outside allowed roots.",
                code=INVALID_WORKING_DIRECTORY,
                details={"path": path_text},
            )
        resolved = resolved_relative

    if not resolved.exists():
        raise CapabilityExecutionError(
            f"Working directory does not exist: {resolved}",
            code=INVALID_WORKING_DIRECTORY,
            details={"path": str(resolved)},
        )
    if not resolved.is_dir():
        raise CapabilityExecutionError(
            f"Working directory is not a directory: {resolved}",
            code=INVALID_WORKING_DIRECTORY,
            details={"path": str(resolved)},
        )
    return resolved


def _matching_root(resolved: Path, allowed_roots: tuple[Path, ...]) -> Path | None:
    for root in allowed_roots:
        if _is_within_root(resolved, root):
            return root
    return None


def _is_within_root(resolved: Path, root: Path) -> bool:
    try:
        resolved.relative_to(root)
    except ValueError:
        return False
    return True
