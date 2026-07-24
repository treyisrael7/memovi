"""Filesystem write operation handlers.

Every path is expected to already be root-scoped via ``resolve_safe_path``.
Handlers never overwrite silently and never return raw exceptions.
"""

from __future__ import annotations

import shutil
from collections.abc import Mapping
from pathlib import Path

from memovi_automation.domain.exceptions import CapabilityExecutionError
from memovi_automation.filesystem.config import FilesystemCapabilityConfig
from memovi_automation.filesystem.errors import (
    ALREADY_EXISTS,
    DESTINATION_REQUIRED,
    DIRECTORY_NOT_EMPTY,
    FILE_NOT_FOUND,
    INVALID_PATH,
    NOT_A_DIRECTORY,
    NOT_A_FILE,
    OVERWRITE_CONFIRMATION_REQUIRED,
    OVERWRITE_REJECTED,
    SAME_PATH,
    UNSAFE_TARGET,
    WRITE_TOO_LARGE,
)
from memovi_automation.filesystem.trash import move_to_trash

CREATE_OPERATIONS = frozenset({"create_file", "create_directory"})
MODIFY_OPERATIONS = frozenset(
    {
        "replace_file_contents",
        "append_to_file",
        "write_file",
    }
)
MOVE_OPERATIONS = frozenset(
    {
        "rename_file",
        "rename_directory",
        "copy_file",
        "copy_directory",
        "move_file",
        "move_directory",
        "move_path",
        "rename_path",
    }
)
DELETE_OPERATIONS = frozenset(
    {
        "delete_file",
        "delete_directory",
        "delete_path",
    }
)

WRITE_OPERATIONS = (
    CREATE_OPERATIONS | MODIFY_OPERATIONS | MOVE_OPERATIONS | DELETE_OPERATIONS
)


def execute_write_operation(
    operation: str,
    *,
    path: Path,
    arguments: Mapping[str, object],
    config: FilesystemCapabilityConfig,
    resolve_path,
    check_cancelled,
) -> dict[str, object]:
    """Dispatch a write operation and return a structured success payload."""
    check_cancelled()
    if operation == "create_file":
        return _create_file(path, arguments=arguments, config=config)
    if operation == "create_directory":
        return _create_directory(path, arguments=arguments, config=config)
    if operation == "replace_file_contents":
        return _replace_file_contents(path, arguments=arguments, config=config)
    if operation == "append_to_file":
        return _append_to_file(path, arguments=arguments, config=config)
    if operation == "write_file":
        return _write_file(path, arguments=arguments, config=config)
    if operation in {"rename_file", "rename_directory", "rename_path"}:
        destination = _resolve_destination(
            arguments,
            resolve_path=resolve_path,
            config=config,
        )
        return _rename_path(
            path,
            destination,
            operation=operation,
            arguments=arguments,
            config=config,
            check_cancelled=check_cancelled,
        )
    if operation in {"copy_file", "copy_directory"}:
        destination = _resolve_destination(
            arguments,
            resolve_path=resolve_path,
            config=config,
        )
        return _copy_path(
            path,
            destination,
            operation=operation,
            arguments=arguments,
            config=config,
            check_cancelled=check_cancelled,
        )
    if operation in {"move_file", "move_directory", "move_path"}:
        destination = _resolve_destination(
            arguments,
            resolve_path=resolve_path,
            config=config,
        )
        return _move_path(
            path,
            destination,
            operation=operation,
            arguments=arguments,
            config=config,
            check_cancelled=check_cancelled,
        )
    if operation in {"delete_file", "delete_directory", "delete_path"}:
        return _delete_path(
            path,
            operation=operation,
            arguments=arguments,
            config=config,
            check_cancelled=check_cancelled,
        )

    raise CapabilityExecutionError(
        f"Unsupported filesystem write operation '{operation}'.",
        code="unsupported_operation",
        details={"operation": operation},
    )


def _success(
    *,
    operation: str,
    target: Path,
    metadata: dict[str, object] | None = None,
    destination: Path | None = None,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "operation": operation,
        "target": str(target),
        "success": True,
        "metadata": metadata or {},
    }
    if destination is not None:
        payload["destination"] = str(destination)
    return payload


def _optional_string(arguments: Mapping[str, object], name: str) -> str | None:
    if name not in arguments or arguments[name] is None:
        return None
    value = arguments[name]
    if not isinstance(value, str) or not value.strip():
        raise CapabilityExecutionError(
            f"Argument '{name}' must be a non-empty string when provided.",
            code=INVALID_PATH if name in {"path", "destination"} else "unsupported_operation",
            details={"argument": name},
        )
    return value.strip()


def _require_content(arguments: Mapping[str, object]) -> str:
    if "content" not in arguments:
        raise CapabilityExecutionError(
            "Argument 'content' is required.",
            code="unsupported_operation",
            details={"argument": "content"},
        )
    value = arguments["content"]
    if not isinstance(value, str):
        raise CapabilityExecutionError(
            "Argument 'content' must be a string.",
            code="unsupported_operation",
            details={"argument": "content"},
        )
    return value


def _encoding(arguments: Mapping[str, object], *, default: str) -> str:
    value = arguments.get("encoding", default)
    if not isinstance(value, str) or not value.strip():
        raise CapabilityExecutionError(
            "Argument 'encoding' must be a non-empty string when provided.",
            code="unsupported_operation",
            details={"argument": "encoding"},
        )
    return value.strip()


def _overwrite_policy(
    arguments: Mapping[str, object],
    *,
    default: str,
) -> str:
    raw = _optional_string(arguments, "overwrite_policy")
    policy = (raw or default).lower()
    if policy not in {"reject", "ask_user", "replace"}:
        raise CapabilityExecutionError(
            "Argument 'overwrite_policy' must be reject, ask_user, or replace.",
            code="unsupported_operation",
            details={"argument": "overwrite_policy", "value": policy},
        )
    return policy


def _delete_mode(arguments: Mapping[str, object], *, default: str) -> str:
    raw = _optional_string(arguments, "delete_mode")
    mode = (raw or default).lower()
    if mode not in {"trash", "permanent"}:
        raise CapabilityExecutionError(
            "Argument 'delete_mode' must be trash or permanent.",
            code="unsupported_operation",
            details={"argument": "delete_mode", "value": mode},
        )
    return mode


def _ensure_write_size(content: str, *, encoding: str, max_write_bytes: int) -> int:
    size = len(content.encode(encoding))
    if size > max_write_bytes:
        raise CapabilityExecutionError(
            f"Content exceeds max_write_bytes ({max_write_bytes}).",
            code=WRITE_TOO_LARGE,
            details={"size_bytes": size, "max_write_bytes": max_write_bytes},
        )
    return size


def _reject_root_target(path: Path, *, allowed_roots: tuple[Path, ...]) -> None:
    for root in allowed_roots:
        if path == root:
            raise CapabilityExecutionError(
                "Refusing to modify an allowed filesystem root.",
                code=UNSAFE_TARGET,
                details={"path": str(path)},
            )


def _handle_existing_destination(
    destination: Path,
    *,
    operation: str,
    policy: str,
) -> None:
    if not destination.exists():
        return
    if policy == "reject":
        raise CapabilityExecutionError(
            f"Destination already exists: {destination}",
            code=OVERWRITE_REJECTED,
            details={
                "operation": operation,
                "path": str(destination),
                "overwrite_policy": policy,
            },
        )
    if policy == "ask_user":
        raise CapabilityExecutionError(
            f"Overwrite confirmation required for: {destination}",
            code=OVERWRITE_CONFIRMATION_REQUIRED,
            details={
                "operation": operation,
                "path": str(destination),
                "overwrite_policy": policy,
            },
        )
    # replace
    if destination.is_dir():
        try:
            shutil.rmtree(destination)
        except OSError as exc:
            raise CapabilityExecutionError(
                f"Failed to replace destination directory: {destination}",
                code=INVALID_PATH,
                details={"path": str(destination), "os_error": type(exc).__name__},
            ) from exc
    else:
        try:
            destination.unlink()
        except OSError as exc:
            raise CapabilityExecutionError(
                f"Failed to replace destination file: {destination}",
                code=INVALID_PATH,
                details={"path": str(destination), "os_error": type(exc).__name__},
            ) from exc


def _resolve_destination(
    arguments: Mapping[str, object],
    *,
    resolve_path,
    config: FilesystemCapabilityConfig,
) -> Path:
    raw = arguments.get("destination")
    if not isinstance(raw, str) or not raw.strip():
        raise CapabilityExecutionError(
            "Argument 'destination' is required.",
            code=DESTINATION_REQUIRED,
            details={"argument": "destination"},
        )
    destination = resolve_path(raw.strip(), allowed_roots=config.allowed_roots)
    _reject_root_target(destination, allowed_roots=config.allowed_roots)
    return destination


def _create_file(
    path: Path,
    *,
    arguments: Mapping[str, object],
    config: FilesystemCapabilityConfig,
) -> dict[str, object]:
    _reject_root_target(path, allowed_roots=config.allowed_roots)
    policy = _overwrite_policy(
        arguments,
        default=config.default_overwrite_policy,
    )
    content = _require_content(arguments)
    encoding = _encoding(arguments, default=config.default_encoding)
    size = _ensure_write_size(
        content,
        encoding=encoding,
        max_write_bytes=config.max_write_bytes,
    )

    if path.exists():
        if path.is_dir():
            raise CapabilityExecutionError(
                f"Path is a directory, not a file: {path}",
                code=NOT_A_FILE,
                details={"path": str(path)},
            )
        if policy == "reject":
            raise CapabilityExecutionError(
                f"File already exists: {path}",
                code=ALREADY_EXISTS,
                details={"path": str(path), "overwrite_policy": policy},
            )
        if policy == "ask_user":
            raise CapabilityExecutionError(
                f"Overwrite confirmation required for: {path}",
                code=OVERWRITE_CONFIRMATION_REQUIRED,
                details={"path": str(path), "overwrite_policy": policy},
            )

    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding=encoding)
    except OSError as exc:
        raise CapabilityExecutionError(
            f"Failed to create file: {path}",
            code=INVALID_PATH,
            details={"path": str(path), "os_error": type(exc).__name__},
        ) from exc

    return _success(
        operation="create_file",
        target=path,
        metadata={
            "encoding": encoding,
            "size_bytes": size,
            "overwrite_policy": policy,
            "created": True,
        },
    )


def _create_directory(
    path: Path,
    *,
    arguments: Mapping[str, object],
    config: FilesystemCapabilityConfig,
) -> dict[str, object]:
    _reject_root_target(path, allowed_roots=config.allowed_roots)
    policy = _overwrite_policy(
        arguments,
        default=config.default_overwrite_policy,
    )
    if path.exists():
        if not path.is_dir():
            raise CapabilityExecutionError(
                f"Path exists and is not a directory: {path}",
                code=NOT_A_DIRECTORY,
                details={"path": str(path)},
            )
        if policy == "reject":
            raise CapabilityExecutionError(
                f"Directory already exists: {path}",
                code=ALREADY_EXISTS,
                details={"path": str(path), "overwrite_policy": policy},
            )
        if policy == "ask_user":
            raise CapabilityExecutionError(
                f"Overwrite confirmation required for: {path}",
                code=OVERWRITE_CONFIRMATION_REQUIRED,
                details={"path": str(path), "overwrite_policy": policy},
            )
        # replace empty directory only
        try:
            next(path.iterdir())
        except StopIteration:
            pass
        else:
            raise CapabilityExecutionError(
                f"Directory is not empty: {path}",
                code=DIRECTORY_NOT_EMPTY,
                details={"path": str(path)},
            )
        return _success(
            operation="create_directory",
            target=path,
            metadata={"overwrite_policy": policy, "already_existed": True},
        )

    try:
        path.mkdir(parents=True, exist_ok=False)
    except OSError as exc:
        raise CapabilityExecutionError(
            f"Failed to create directory: {path}",
            code=INVALID_PATH,
            details={"path": str(path), "os_error": type(exc).__name__},
        ) from exc

    return _success(
        operation="create_directory",
        target=path,
        metadata={"overwrite_policy": policy, "created": True},
    )


def _replace_file_contents(
    path: Path,
    *,
    arguments: Mapping[str, object],
    config: FilesystemCapabilityConfig,
) -> dict[str, object]:
    _reject_root_target(path, allowed_roots=config.allowed_roots)
    if not path.exists():
        raise CapabilityExecutionError(
            f"Path not found: {path}",
            code=FILE_NOT_FOUND,
            details={"path": str(path)},
        )
    if not path.is_file():
        raise CapabilityExecutionError(
            f"Path is not a regular file: {path}",
            code=NOT_A_FILE,
            details={"path": str(path)},
        )

    content = _require_content(arguments)
    encoding = _encoding(arguments, default=config.default_encoding)
    size = _ensure_write_size(
        content,
        encoding=encoding,
        max_write_bytes=config.max_write_bytes,
    )
    try:
        path.write_text(content, encoding=encoding)
    except OSError as exc:
        raise CapabilityExecutionError(
            f"Failed to replace file contents: {path}",
            code=INVALID_PATH,
            details={"path": str(path), "os_error": type(exc).__name__},
        ) from exc

    return _success(
        operation="replace_file_contents",
        target=path,
        metadata={"encoding": encoding, "size_bytes": size, "replaced": True},
    )


def _append_to_file(
    path: Path,
    *,
    arguments: Mapping[str, object],
    config: FilesystemCapabilityConfig,
) -> dict[str, object]:
    _reject_root_target(path, allowed_roots=config.allowed_roots)
    if path.exists() and not path.is_file():
        raise CapabilityExecutionError(
            f"Path is not a regular file: {path}",
            code=NOT_A_FILE,
            details={"path": str(path)},
        )

    content = _require_content(arguments)
    encoding = _encoding(arguments, default=config.default_encoding)
    size = _ensure_write_size(
        content,
        encoding=encoding,
        max_write_bytes=config.max_write_bytes,
    )
    created = not path.exists()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding=encoding) as handle:
            handle.write(content)
    except OSError as exc:
        raise CapabilityExecutionError(
            f"Failed to append to file: {path}",
            code=INVALID_PATH,
            details={"path": str(path), "os_error": type(exc).__name__},
        ) from exc

    return _success(
        operation="append_to_file",
        target=path,
        metadata={
            "encoding": encoding,
            "appended_bytes": size,
            "created": created,
        },
    )


def _write_file(
    path: Path,
    *,
    arguments: Mapping[str, object],
    config: FilesystemCapabilityConfig,
) -> dict[str, object]:
    """Compatibility alias: create when missing, otherwise honor overwrite policy."""
    if path.exists():
        policy = _overwrite_policy(
            arguments,
            default=config.default_overwrite_policy,
        )
        if policy == "replace":
            result = _replace_file_contents(path, arguments=arguments, config=config)
            result["operation"] = "write_file"
            return result
        if policy == "ask_user":
            raise CapabilityExecutionError(
                f"Overwrite confirmation required for: {path}",
                code=OVERWRITE_CONFIRMATION_REQUIRED,
                details={"path": str(path), "overwrite_policy": policy},
            )
        raise CapabilityExecutionError(
            f"File already exists: {path}",
            code=ALREADY_EXISTS,
            details={"path": str(path), "overwrite_policy": policy},
        )
    result = _create_file(path, arguments=arguments, config=config)
    result["operation"] = "write_file"
    return result


def _ensure_source_file(path: Path) -> None:
    if not path.exists():
        raise CapabilityExecutionError(
            f"Path not found: {path}",
            code=FILE_NOT_FOUND,
            details={"path": str(path)},
        )
    if not path.is_file():
        raise CapabilityExecutionError(
            f"Path is not a regular file: {path}",
            code=NOT_A_FILE,
            details={"path": str(path)},
        )


def _ensure_source_directory(path: Path) -> None:
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


def _rename_path(
    source: Path,
    destination: Path,
    *,
    operation: str,
    arguments: Mapping[str, object],
    config: FilesystemCapabilityConfig,
    check_cancelled,
) -> dict[str, object]:
    _reject_root_target(source, allowed_roots=config.allowed_roots)
    if source == destination:
        raise CapabilityExecutionError(
            "Source and destination paths are the same.",
            code=SAME_PATH,
            details={"path": str(source)},
        )

    resolved_operation = operation
    if operation == "rename_path":
        if source.is_dir():
            resolved_operation = "rename_directory"
        elif source.is_file():
            resolved_operation = "rename_file"
        else:
            raise CapabilityExecutionError(
                f"Path not found: {source}",
                code=FILE_NOT_FOUND,
                details={"path": str(source)},
            )
    if resolved_operation == "rename_file":
        _ensure_source_file(source)
    else:
        _ensure_source_directory(source)

    policy = _overwrite_policy(arguments, default=config.default_overwrite_policy)
    check_cancelled()
    _handle_existing_destination(destination, operation=resolved_operation, policy=policy)
    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
        source.rename(destination)
    except OSError as exc:
        raise CapabilityExecutionError(
            f"Failed to rename path: {source}",
            code=INVALID_PATH,
            details={
                "path": str(source),
                "destination": str(destination),
                "os_error": type(exc).__name__,
            },
        ) from exc

    return _success(
        operation=resolved_operation,
        target=source,
        destination=destination,
        metadata={"overwrite_policy": policy, "renamed": True},
    )


def _copy_path(
    source: Path,
    destination: Path,
    *,
    operation: str,
    arguments: Mapping[str, object],
    config: FilesystemCapabilityConfig,
    check_cancelled,
) -> dict[str, object]:
    _reject_root_target(source, allowed_roots=config.allowed_roots)
    if source == destination:
        raise CapabilityExecutionError(
            "Source and destination paths are the same.",
            code=SAME_PATH,
            details={"path": str(source)},
        )

    if operation == "copy_file":
        _ensure_source_file(source)
    else:
        _ensure_source_directory(source)

    policy = _overwrite_policy(arguments, default=config.default_overwrite_policy)
    check_cancelled()
    _handle_existing_destination(destination, operation=operation, policy=policy)

    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
        if operation == "copy_file":
            shutil.copy2(source, destination)
        else:
            shutil.copytree(source, destination)
    except OSError as exc:
        raise CapabilityExecutionError(
            f"Failed to copy path: {source}",
            code=INVALID_PATH,
            details={
                "path": str(source),
                "destination": str(destination),
                "os_error": type(exc).__name__,
            },
        ) from exc

    return _success(
        operation=operation,
        target=source,
        destination=destination,
        metadata={"overwrite_policy": policy, "copied": True},
    )


def _move_path(
    source: Path,
    destination: Path,
    *,
    operation: str,
    arguments: Mapping[str, object],
    config: FilesystemCapabilityConfig,
    check_cancelled,
) -> dict[str, object]:
    _reject_root_target(source, allowed_roots=config.allowed_roots)
    if source == destination:
        raise CapabilityExecutionError(
            "Source and destination paths are the same.",
            code=SAME_PATH,
            details={"path": str(source)},
        )

    resolved_operation = operation
    if operation == "move_path":
        if source.is_dir():
            resolved_operation = "move_directory"
        elif source.is_file():
            resolved_operation = "move_file"
        else:
            raise CapabilityExecutionError(
                f"Path not found: {source}",
                code=FILE_NOT_FOUND,
                details={"path": str(source)},
            )
    if resolved_operation == "move_file":
        _ensure_source_file(source)
    else:
        _ensure_source_directory(source)

    policy = _overwrite_policy(arguments, default=config.default_overwrite_policy)
    check_cancelled()
    _handle_existing_destination(destination, operation=resolved_operation, policy=policy)

    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(source), str(destination))
    except OSError as exc:
        raise CapabilityExecutionError(
            f"Failed to move path: {source}",
            code=INVALID_PATH,
            details={
                "path": str(source),
                "destination": str(destination),
                "os_error": type(exc).__name__,
            },
        ) from exc

    return _success(
        operation=resolved_operation,
        target=source,
        destination=destination,
        metadata={"overwrite_policy": policy, "moved": True},
    )


def _delete_path(
    path: Path,
    *,
    operation: str,
    arguments: Mapping[str, object],
    config: FilesystemCapabilityConfig,
    check_cancelled,
) -> dict[str, object]:
    _reject_root_target(path, allowed_roots=config.allowed_roots)
    if not path.exists():
        raise CapabilityExecutionError(
            f"Path not found: {path}",
            code=FILE_NOT_FOUND,
            details={"path": str(path)},
        )

    resolved_operation = operation
    if operation == "delete_path":
        resolved_operation = "delete_directory" if path.is_dir() else "delete_file"
    if resolved_operation == "delete_file":
        _ensure_source_file(path)
    else:
        _ensure_source_directory(path)

    mode = _delete_mode(arguments, default=config.default_delete_mode)
    check_cancelled()

    if mode == "trash":
        trash_meta = move_to_trash(path)
        return _success(
            operation=resolved_operation,
            target=path,
            metadata={
                **trash_meta,
                "deleted": True,
            },
        )

    if not config.allow_permanent_delete:
        raise CapabilityExecutionError(
            "Permanent deletion is disabled for this filesystem capability.",
            code="unsupported_operation",
            details={"delete_mode": mode, "path": str(path)},
        )

    try:
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()
    except OSError as exc:
        raise CapabilityExecutionError(
            f"Failed to permanently delete path: {path}",
            code=INVALID_PATH,
            details={"path": str(path), "os_error": type(exc).__name__},
        ) from exc

    return _success(
        operation=resolved_operation,
        target=path,
        metadata={
            "delete_mode": "permanent",
            "undo_available": False,
            "undo_message": "Permanently deleted. This action cannot be undone.",
            "deleted": True,
        },
    )
