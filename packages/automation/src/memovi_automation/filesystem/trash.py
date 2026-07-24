"""Move paths to the system Recycle Bin / Trash when available."""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

from memovi_automation.domain.exceptions import CapabilityExecutionError
from memovi_automation.filesystem.errors import INVALID_PATH, TRASH_UNAVAILABLE


def move_to_trash(path: Path) -> dict[str, object]:
    """Move ``path`` to the platform trash/recycle bin.

    Returns metadata describing the trash action. Raises
    ``CapabilityExecutionError`` with ``trash_unavailable`` when the platform
    cannot perform a recoverable delete.
    """
    if not path.exists():
        raise CapabilityExecutionError(
            f"Path not found: {path}",
            code=INVALID_PATH,
            details={"path": str(path)},
        )

    if sys.platform == "win32":
        return _trash_windows(path)
    if sys.platform == "darwin":
        return _trash_macos(path)
    return _trash_xdg(path)


def _trash_windows(path: Path) -> dict[str, object]:
    import ctypes
    from ctypes import wintypes

    class SHFILEOPSTRUCTW(ctypes.Structure):
        _fields_ = [
            ("hwnd", wintypes.HWND),
            ("wFunc", wintypes.UINT),
            ("pFrom", wintypes.LPCWSTR),
            ("pTo", wintypes.LPCWSTR),
            ("fFlags", wintypes.WORD),
            ("fAnyOperationsAborted", wintypes.BOOL),
            ("hNameMappings", wintypes.LPVOID),
            ("lpszProgressTitle", wintypes.LPCWSTR),
        ]

    FO_DELETE = 3
    FOF_ALLOWUNDO = 0x0040
    FOF_NOCONFIRMATION = 0x0010
    FOF_NOERRORUI = 0x0400
    FOF_SILENT = 0x0004

    # Double-null-terminated path list required by SHFileOperationW.
    from_path = str(path) + "\0\0"
    op = SHFILEOPSTRUCTW(
        hwnd=None,
        wFunc=FO_DELETE,
        pFrom=from_path,
        pTo=None,
        fFlags=FOF_ALLOWUNDO | FOF_NOCONFIRMATION | FOF_NOERRORUI | FOF_SILENT,
        fAnyOperationsAborted=False,
        hNameMappings=None,
        lpszProgressTitle=None,
    )
    result = ctypes.windll.shell32.SHFileOperationW(ctypes.byref(op))
    if result != 0 or op.fAnyOperationsAborted:
        raise CapabilityExecutionError(
            f"Failed to move path to Recycle Bin: {path}",
            code=TRASH_UNAVAILABLE,
            details={"path": str(path), "shell_result": result},
        )
    return {
        "delete_mode": "trash",
        "trash_backend": "windows_recycle_bin",
        "undo_available": True,
        "undo_message": (
            "Moved to the Recycle Bin. Restore from the Recycle Bin if needed."
        ),
    }


def _trash_macos(path: Path) -> dict[str, object]:
    import subprocess

    script = f'tell application "Finder" to delete POSIX file "{path}"'
    completed = subprocess.run(
        ["osascript", "-e", script],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0 or path.exists():
        raise CapabilityExecutionError(
            f"Failed to move path to Trash: {path}",
            code=TRASH_UNAVAILABLE,
            details={
                "path": str(path),
                "stderr": (completed.stderr or "").strip()[:200],
            },
        )
    return {
        "delete_mode": "trash",
        "trash_backend": "macos_finder",
        "undo_available": True,
        "undo_message": "Moved to Trash. Restore from Trash if needed.",
    }


def _trash_xdg(path: Path) -> dict[str, object]:
    # Prefer gio when available (GNOME / FreeDesktop).
    gio = shutil.which("gio")
    if gio is not None:
        import subprocess

        completed = subprocess.run(
            [gio, "trash", str(path)],
            check=False,
            capture_output=True,
            text=True,
        )
        if completed.returncode == 0 and not path.exists():
            return {
                "delete_mode": "trash",
                "trash_backend": "gio",
                "undo_available": True,
                "undo_message": "Moved to Trash. Restore from Trash if needed.",
            }

    trash_home = Path(
        os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"),
    ) / "Trash"
    files_dir = trash_home / "files"
    info_dir = trash_home / "info"
    try:
        files_dir.mkdir(parents=True, exist_ok=True)
        info_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise CapabilityExecutionError(
            f"Trash is unavailable for path: {path}",
            code=TRASH_UNAVAILABLE,
            details={"path": str(path), "os_error": type(exc).__name__},
        ) from exc

    destination = files_dir / path.name
    counter = 1
    while destination.exists():
        destination = files_dir / f"{path.name}.{counter}"
        counter += 1

    info_path = info_dir / f"{destination.name}.trashinfo"
    from datetime import UTC, datetime

    deletion_date = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S")
    info_body = (
        "[Trash Info]\n"
        f"Path={path.resolve()}\n"
        f"DeletionDate={deletion_date}\n"
    )
    try:
        info_path.write_text(info_body, encoding="utf-8")
        shutil.move(str(path), str(destination))
    except OSError as exc:
        info_path.unlink(missing_ok=True)
        raise CapabilityExecutionError(
            f"Failed to move path to Trash: {path}",
            code=TRASH_UNAVAILABLE,
            details={"path": str(path), "os_error": type(exc).__name__},
        ) from exc

    return {
        "delete_mode": "trash",
        "trash_backend": "xdg",
        "undo_available": True,
        "undo_message": "Moved to Trash. Restore from Trash if needed.",
    }
