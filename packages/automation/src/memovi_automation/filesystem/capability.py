from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Final

from memovi_automation.application.services.capability_registry import CapabilityRegistry
from memovi_automation.domain.exceptions import CapabilityExecutionError
from memovi_automation.domain.value_objects import (
    FILESYSTEM_READ,
    FILESYSTEM_WRITE,
    CapabilityContext,
    CapabilityMetadata,
    CapabilityParameter,
    CapabilityPermission,
    CapabilityRequest,
)
from memovi_automation.filesystem.config import FilesystemCapabilityConfig
from memovi_automation.filesystem.errors import (
    FILE_NOT_FOUND,
    FILE_TOO_LARGE,
    INVALID_PATH,
    NOT_A_DIRECTORY,
    NOT_A_FILE,
    NOT_TEXT_FILE,
    PERMISSION_DENIED,
    UNSUPPORTED_OPERATION,
)
from memovi_automation.filesystem.path_safety import resolve_safe_path

CAPABILITY_ID: Final = "filesystem"

READ_OPERATIONS: Final[frozenset[str]] = frozenset(
    {
        "read_file",
        "read_directory",
        "list_directory",
        "exists",
        "get_metadata",
    }
)

# Reserved for future write milestones — kept here so operation routing and
# permission selection do not need a redesign when writes land.
WRITE_OPERATIONS: Final[frozenset[str]] = frozenset(
    {
        "write_file",
        "delete_path",
        "move_path",
        "rename_path",
    }
)

_ALL_KNOWN_OPERATIONS: Final[frozenset[str]] = READ_OPERATIONS | WRITE_OPERATIONS


class FilesystemCapability:
    """Read-only filesystem capability — reference production Capability.

    Discoverable through ``CapabilityRegistry`` under id ``filesystem``.
    Declares ``filesystem.read`` now; ``filesystem.write`` is reserved for
    future write operations and enforced per-operation when those land.
    """

    def __init__(self, config: FilesystemCapabilityConfig) -> None:
        self._config = config

    @property
    def config(self) -> FilesystemCapabilityConfig:
        return self._config

    def metadata(self) -> CapabilityMetadata:
        return CapabilityMetadata(
            id=CAPABILITY_ID,
            description=(
                "Read-only filesystem access restricted to configured roots. "
                "Supports read_file, read_directory, list_directory, exists, "
                "and get_metadata."
            ),
            permissions=(FILESYSTEM_READ,),
            parameters=(
                CapabilityParameter(
                    name="operation",
                    type="string",
                    description=(
                        "Filesystem operation: read_file, read_directory, "
                        "list_directory, exists, or get_metadata."
                    ),
                ),
                CapabilityParameter(
                    name="path",
                    type="string",
                    description=(
                        "Absolute path under an allowed root, or a path relative "
                        "to an allowed root."
                    ),
                ),
                CapabilityParameter(
                    name="encoding",
                    type="string",
                    description="Text encoding for read_file (default: utf-8).",
                    required=False,
                ),
            ),
        )

    def execute(self, request: CapabilityRequest, context: CapabilityContext) -> object:
        context.check_cancelled()
        operation = _require_string_argument(request.arguments, "operation")
        raw_path = request.arguments.get("path")

        permission = _permission_for_operation(operation)
        if not context.has_permission(permission):
            raise CapabilityExecutionError(
                f"Missing required permission '{permission}'.",
                code=PERMISSION_DENIED,
                details={
                    "permission": permission.name,
                    "operation": operation,
                },
            )

        if operation in WRITE_OPERATIONS:
            raise CapabilityExecutionError(
                f"Filesystem operation '{operation}' is not supported yet.",
                code=UNSUPPORTED_OPERATION,
                details={"operation": operation},
            )
        if operation not in READ_OPERATIONS:
            raise CapabilityExecutionError(
                f"Unsupported filesystem operation '{operation}'.",
                code=UNSUPPORTED_OPERATION,
                details={"operation": operation},
            )

        path = resolve_safe_path(raw_path, allowed_roots=self._config.allowed_roots)
        context.check_cancelled()

        if operation == "exists":
            return _exists_result(path)
        if operation == "get_metadata":
            return _metadata_result(path)
        if operation == "list_directory":
            return _list_directory_result(path)
        if operation == "read_directory":
            return _read_directory_result(path)
        if operation == "read_file":
            encoding = _optional_encoding(
                request.arguments,
                default=self._config.default_encoding,
            )
            return _read_file_result(
                path,
                encoding=encoding,
                max_read_bytes=self._config.max_read_bytes,
            )

        raise CapabilityExecutionError(
            f"Unsupported filesystem operation '{operation}'.",
            code=UNSUPPORTED_OPERATION,
            details={"operation": operation},
        )


def register_filesystem_capability(
    registry: CapabilityRegistry,
    config: FilesystemCapabilityConfig,
) -> FilesystemCapability:
    """Register the Filesystem Capability on a CapabilityRegistry."""
    capability = FilesystemCapability(config)
    registry.register(capability)
    return capability


def _permission_for_operation(operation: str) -> CapabilityPermission:
    if operation in WRITE_OPERATIONS:
        return FILESYSTEM_WRITE
    if operation in READ_OPERATIONS:
        return FILESYSTEM_READ
    # Unknown operations still require read permission to inspect; unsupported
    # is reported after the permission check.
    if operation in _ALL_KNOWN_OPERATIONS:
        return FILESYSTEM_READ
    return FILESYSTEM_READ


def _require_string_argument(arguments: Mapping[str, object], name: str) -> str:
    value = arguments.get(name)
    if not isinstance(value, str) or not value.strip():
        raise CapabilityExecutionError(
            f"Argument '{name}' must be a non-empty string.",
            code=INVALID_PATH if name == "path" else UNSUPPORTED_OPERATION,
            details={"argument": name},
        )
    return value.strip()


def _optional_encoding(arguments: Mapping[str, object], *, default: str) -> str:
    value = arguments.get("encoding", default)
    if not isinstance(value, str) or not value.strip():
        raise CapabilityExecutionError(
            "Argument 'encoding' must be a non-empty string when provided.",
            code=UNSUPPORTED_OPERATION,
            details={"argument": "encoding"},
        )
    return value.strip()


def _exists_result(path: Path) -> dict[str, object]:
    return {
        "operation": "exists",
        "path": str(path),
        "exists": path.exists(),
        "is_file": path.is_file(),
        "is_directory": path.is_dir(),
    }


def _metadata_result(path: Path) -> dict[str, object]:
    if not path.exists():
        raise CapabilityExecutionError(
            f"Path not found: {path}",
            code=FILE_NOT_FOUND,
            details={"path": str(path)},
        )
    stat = path.stat()
    return {
        "operation": "get_metadata",
        "path": str(path),
        "exists": True,
        "is_file": path.is_file(),
        "is_directory": path.is_dir(),
        "size_bytes": stat.st_size,
        "modified_at": datetime.fromtimestamp(stat.st_mtime, tz=UTC).isoformat(),
    }


def _list_directory_result(path: Path) -> dict[str, object]:
    _ensure_directory(path)
    entries = sorted(entry.name for entry in path.iterdir())
    return {
        "operation": "list_directory",
        "path": str(path),
        "entries": entries,
        "count": len(entries),
    }


def _read_directory_result(path: Path) -> dict[str, object]:
    _ensure_directory(path)
    entries: list[dict[str, object]] = []
    for entry in sorted(path.iterdir(), key=lambda item: item.name):
        item: dict[str, object] = {
            "name": entry.name,
            "path": str(entry.resolve(strict=False)),
            "is_file": entry.is_file(),
            "is_directory": entry.is_dir(),
        }
        if entry.is_file():
            item["size_bytes"] = entry.stat().st_size
        entries.append(item)
    return {
        "operation": "read_directory",
        "path": str(path),
        "entries": entries,
        "count": len(entries),
    }


def _read_file_result(
    path: Path,
    *,
    encoding: str,
    max_read_bytes: int,
) -> dict[str, object]:
    if not path.exists():
        raise CapabilityExecutionError(
            f"Path not found: {path}",
            code=FILE_NOT_FOUND,
            details={"path": str(path)},
        )
    if path.is_dir():
        raise CapabilityExecutionError(
            f"Path is a directory, not a file: {path}",
            code=NOT_A_FILE,
            details={"path": str(path)},
        )
    if not path.is_file():
        raise CapabilityExecutionError(
            f"Path is not a regular file: {path}",
            code=NOT_A_FILE,
            details={"path": str(path)},
        )

    size = path.stat().st_size
    if size > max_read_bytes:
        raise CapabilityExecutionError(
            f"File exceeds max_read_bytes ({max_read_bytes}).",
            code=FILE_TOO_LARGE,
            details={
                "path": str(path),
                "size_bytes": size,
                "max_read_bytes": max_read_bytes,
            },
        )

    try:
        content = path.read_text(encoding=encoding)
    except UnicodeDecodeError as exc:
        raise CapabilityExecutionError(
            f"File is not valid text for encoding '{encoding}'.",
            code=NOT_TEXT_FILE,
            details={"path": str(path), "encoding": encoding},
        ) from exc
    except OSError as exc:
        raise CapabilityExecutionError(
            f"Failed to read file: {path}",
            code=INVALID_PATH,
            details={"path": str(path), "os_error": type(exc).__name__},
        ) from exc

    return {
        "operation": "read_file",
        "path": str(path),
        "encoding": encoding,
        "size_bytes": size,
        "content": content,
    }


def _ensure_directory(path: Path) -> None:
    if not path.exists():
        raise CapabilityExecutionError(
            f"Path not found: {path}",
            code=FILE_NOT_FOUND,
            details={"path": str(path)},
        )
    if not path.is_dir():
        raise CapabilityExecutionError(
            f"Path is not a directory: {path}",
            code=NOT_A_DIRECTORY,
            details={"path": str(path)},
        )
