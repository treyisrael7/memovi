from pathlib import Path

from memovi_automation.domain.exceptions import CapabilityExecutionError
from memovi_automation.filesystem.errors import INVALID_PATH


def resolve_safe_path(raw_path: object, *, allowed_roots: tuple[Path, ...]) -> Path:
    """Normalize ``raw_path`` and ensure it resolves under an allowed root.

    Rejects blank paths, null bytes, and path-traversal attempts that escape
    configured roots (including symlink escapes after resolve).
    """
    if not isinstance(raw_path, str):
        raise CapabilityExecutionError(
            "Filesystem path must be a string.",
            code=INVALID_PATH,
            details={"path_type": type(raw_path).__name__},
        )

    path_text = raw_path.strip()
    if not path_text:
        raise CapabilityExecutionError(
            "Filesystem path is required.",
            code=INVALID_PATH,
        )
    if "\x00" in path_text:
        raise CapabilityExecutionError(
            "Filesystem path contains a null byte.",
            code=INVALID_PATH,
            details={"path": path_text},
        )

    candidate = Path(path_text)
    if candidate.is_absolute():
        resolved = candidate.resolve(strict=False)
        root = _matching_root(resolved, allowed_roots)
        if root is None:
            raise CapabilityExecutionError(
                "Filesystem path is outside allowed roots.",
                code=INVALID_PATH,
                details={"path": path_text},
            )
        return resolved

    # Relative paths are tried against each allowed root in order.
    # The first root under which the path does not escape is accepted.
    # Existence is not required here — callers decide not-found semantics.
    for root in allowed_roots:
        resolved = (root / candidate).resolve(strict=False)
        if _is_within_root(resolved, root):
            return resolved

    raise CapabilityExecutionError(
        "Filesystem path is outside allowed roots.",
        code=INVALID_PATH,
        details={"path": path_text},
    )


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
