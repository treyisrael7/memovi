from pathlib import Path

from memovi_automation.domain.exceptions import CapabilityExecutionError
from memovi_automation.git.errors import INVALID_REPOSITORY, REPOSITORY_NOT_FOUND


def resolve_repository_path(
    raw_path: object,
    *,
    allowed_roots: tuple[Path, ...],
) -> Path:
    """Normalize a repository path and ensure it resolves under an allowed root."""
    if not isinstance(raw_path, str):
        raise CapabilityExecutionError(
            "Repository path must be a string.",
            code=INVALID_REPOSITORY,
            details={"path_type": type(raw_path).__name__},
        )

    path_text = raw_path.strip()
    if not path_text:
        raise CapabilityExecutionError(
            "Repository path is required.",
            code=INVALID_REPOSITORY,
        )
    if "\x00" in path_text:
        raise CapabilityExecutionError(
            "Repository path contains a null byte.",
            code=INVALID_REPOSITORY,
            details={"path": path_text},
        )

    candidate = Path(path_text)
    if candidate.is_absolute():
        resolved = candidate.resolve(strict=False)
        if _matching_root(resolved, allowed_roots) is None:
            raise CapabilityExecutionError(
                "Repository path is outside allowed roots.",
                code=INVALID_REPOSITORY,
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
                "Repository path is outside allowed roots.",
                code=INVALID_REPOSITORY,
                details={"path": path_text},
            )
        resolved = resolved_relative

    if not resolved.exists():
        raise CapabilityExecutionError(
            f"Repository path does not exist: {resolved}",
            code=REPOSITORY_NOT_FOUND,
            details={"path": str(resolved)},
        )
    if not resolved.is_dir():
        raise CapabilityExecutionError(
            f"Repository path is not a directory: {resolved}",
            code=INVALID_REPOSITORY,
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
