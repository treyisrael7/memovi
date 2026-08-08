"""Filesystem Connector — first production connector on the Connector Framework."""

from __future__ import annotations

import hashlib
import json
import mimetypes
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath

from memovi_connectors.application.ports import DocumentImportPort
from memovi_connectors.domain.entities import FilesystemFolderConnection
from memovi_connectors.domain.repositories import FilesystemFolderRepository
from memovi_connectors.domain.value_objects import (
    CONNECTOR_FILESYSTEM,
    AuthCredentialRef,
    ConnectorConfiguration,
    ConnectorExecutionContext,
    ConnectorHealth,
    ConnectorMetadata,
    ConnectorResult,
    NormalizedImportItem,
    NormalizedSourceMetadata,
)

_EXTENSION_MIME_TYPES: dict[str, str] = {
    ".txt": "text/plain",
    ".md": "text/markdown",
    ".markdown": "text/markdown",
    ".pdf": "application/pdf",
}

_SUPPORTED_EXTENSIONS = frozenset(_EXTENSION_MIME_TYPES)


@dataclass(frozen=True, slots=True)
class _FileSnapshot:
    relative_path: str
    absolute_path: Path
    size: int
    mtime_ns: int
    sha256: str
    content: bytes
    created_at: datetime | None
    modified_at: datetime


class FilesystemConnector:
    """Import and synchronize a local folder into Documents.

    Folder registrations are stored separately; sync context metadata must
    include ``folder_id``. Change detection uses path inventory + content
    hashes. Rename detection matches vanished/appeared files by content hash
    within a single sync pass.

    ``document_import`` and ``folders`` may be bound at construction (tests) or
    at request time via :meth:`configure_runtime` (composition root sessions).
    """

    def __init__(
        self,
        *,
        document_import: DocumentImportPort | None = None,
        folders: FilesystemFolderRepository | None = None,
        enabled: bool = True,
    ) -> None:
        self._document_import = document_import
        self._folders = folders
        self._enabled = enabled
        self._metadata = ConnectorMetadata(
            connector_id=CONNECTOR_FILESYSTEM,
            display_name="Filesystem",
            description=(
                "Import and synchronize local folders (notes, Obsidian vaults, "
                "docs) into the Documents pipeline."
            ),
            source_category="filesystem",
            auth_methods=("none",),
            supports_incremental_sync=True,
            supports_delete_detection=True,
        )
        self._config = ConnectorConfiguration(
            connector_id=CONNECTOR_FILESYSTEM,
            enabled=enabled,
            auth=AuthCredentialRef(method="none"),
        )

    def configure_runtime(
        self,
        *,
        document_import: DocumentImportPort,
        folders: FilesystemFolderRepository,
    ) -> None:
        """Bind request-scoped Documents handoff and folder persistence."""
        self._document_import = document_import
        self._folders = folders

    def connector_id(self) -> str:
        return CONNECTOR_FILESYSTEM

    def metadata(self) -> ConnectorMetadata:
        return self._metadata

    def configuration(self) -> ConnectorConfiguration:
        return self._config

    def health(self) -> ConnectorHealth:
        if not self._enabled:
            return ConnectorHealth(
                connector_id=CONNECTOR_FILESYSTEM,
                status="unavailable",
                message="Filesystem connector is disabled.",
            )
        return ConnectorHealth(
            connector_id=CONNECTOR_FILESYSTEM,
            status="healthy",
            message="Filesystem connector is ready. Sync status is tracked per folder.",
        )

    def sync(self, context: ConnectorExecutionContext) -> ConnectorResult:
        if context.connector_id != CONNECTOR_FILESYSTEM:
            return ConnectorResult.failure_result(
                connector_id=CONNECTOR_FILESYSTEM,
                sync_mode=context.sync_mode,
                error_code="invalid_context",
                error_message="Execution context connector_id does not match filesystem.",
            )
        if not self._enabled:
            return ConnectorResult.failure_result(
                connector_id=CONNECTOR_FILESYSTEM,
                sync_mode=context.sync_mode,
                error_code="unavailable",
                error_message="Filesystem connector is disabled.",
            )
        if self._document_import is None or self._folders is None:
            return ConnectorResult.failure_result(
                connector_id=CONNECTOR_FILESYSTEM,
                sync_mode=context.sync_mode,
                error_code="not_configured",
                error_message=(
                    "Filesystem connector runtime dependencies are not configured."
                ),
            )

        folder_id = context.metadata.get("folder_id")
        if not isinstance(folder_id, str) or not folder_id.strip():
            return ConnectorResult.failure_result(
                connector_id=CONNECTOR_FILESYSTEM,
                sync_mode=context.sync_mode,
                error_code="missing_folder",
                error_message="Filesystem sync requires metadata.folder_id.",
            )

        folder = self._folders.get_by_id(folder_id.strip(), workspace_id=context.workspace_id)
        if folder is None:
            return ConnectorResult.failure_result(
                connector_id=CONNECTOR_FILESYSTEM,
                sync_mode=context.sync_mode,
                error_code="folder_not_found",
                error_message=f"Filesystem folder '{folder_id}' was not found.",
            )

        root = Path(folder.root_path)
        if not root.exists() or not root.is_dir():
            updated = folder.with_sync_state(
                sync_status="error",
                last_error=f"Root path does not exist or is not a directory: {folder.root_path}",
            )
            self._folders.save(updated)
            return ConnectorResult.failure_result(
                connector_id=CONNECTOR_FILESYSTEM,
                sync_mode=context.sync_mode,
                error_code="invalid_root",
                error_message=updated.last_error or "Invalid root path.",
            )

        syncing = folder.with_sync_state(sync_status="syncing", last_error=None)
        self._folders.save(syncing)

        try:
            return self._run_sync(context=context, folder=syncing, root=root.resolve())
        except OSError as exc:
            failed = syncing.with_sync_state(
                sync_status="error",
                last_error=str(exc),
            )
            self._folders.save(failed)
            return ConnectorResult.failure_result(
                connector_id=CONNECTOR_FILESYSTEM,
                sync_mode=context.sync_mode,
                error_code="filesystem_error",
                error_message=str(exc),
            )

    def _run_sync(
        self,
        *,
        context: ConnectorExecutionContext,
        folder: FilesystemFolderConnection,
        root: Path,
    ) -> ConnectorResult:
        previous = _decode_cursor(context.cursor or folder.sync_cursor)
        current = self._scan_folder(root)

        previous_paths = set(previous.keys())
        current_paths = set(current.keys())
        vanished = previous_paths - current_paths
        appeared = current_paths - previous_paths
        shared = previous_paths & current_paths

        # Practical rename detection: match vanished ↔ appeared by content hash.
        rename_map: dict[str, str] = {}
        unmatched_vanished = set(vanished)
        unmatched_appeared = set(appeared)
        hash_to_vanished: dict[str, str] = {
            previous[path]["sha256"]: path
            for path in vanished
            if previous.get(path, {}).get("sha256")
        }
        for new_path in list(unmatched_appeared):
            digest = current[new_path].sha256
            old_path = hash_to_vanished.get(digest)
            if old_path is None or old_path not in unmatched_vanished:
                continue
            rename_map[old_path] = new_path
            unmatched_vanished.discard(old_path)
            unmatched_appeared.discard(new_path)

        items: list[NormalizedImportItem] = []
        imported = 0
        updated = 0
        deleted = 0
        skipped = 0

        for old_path, new_path in rename_map.items():
            # Rename = delete old identity + upsert new path (same content).
            delete_item = self._build_item(
                folder=folder,
                context=context,
                snapshot=current[new_path],
                relative_path=old_path,
                change_kind="delete",
                content=b"",
            )
            self._document_import.import_item(delete_item)
            items.append(delete_item)
            deleted += 1

            upsert_item = self._build_item(
                folder=folder,
                context=context,
                snapshot=current[new_path],
                relative_path=new_path,
                change_kind="upsert",
                content=current[new_path].content,
            )
            self._document_import.import_item(upsert_item)
            items.append(upsert_item)
            imported += 1

        for relative_path in sorted(unmatched_vanished):
            item = self._build_item(
                folder=folder,
                context=context,
                snapshot=None,
                relative_path=relative_path,
                change_kind="delete",
                content=b"",
            )
            self._document_import.import_item(item)
            items.append(item)
            deleted += 1

        for relative_path in sorted(unmatched_appeared):
            snapshot = current[relative_path]
            item = self._build_item(
                folder=folder,
                context=context,
                snapshot=snapshot,
                relative_path=relative_path,
                change_kind="upsert",
                content=snapshot.content,
            )
            self._document_import.import_item(item)
            items.append(item)
            imported += 1

        for relative_path in sorted(shared):
            snapshot = current[relative_path]
            prior = previous[relative_path]
            unchanged = (
                prior.get("sha256") == snapshot.sha256
                and prior.get("size") == snapshot.size
                and prior.get("mtime_ns") == snapshot.mtime_ns
            )
            if unchanged and context.sync_mode == "incremental":
                skipped += 1
                continue
            item = self._build_item(
                folder=folder,
                context=context,
                snapshot=snapshot,
                relative_path=relative_path,
                change_kind="upsert",
                content=snapshot.content,
            )
            self._document_import.import_item(item)
            items.append(item)
            updated += 1

        new_cursor = _encode_cursor(
            {
                path: {
                    "sha256": snap.sha256,
                    "size": snap.size,
                    "mtime_ns": snap.mtime_ns,
                }
                for path, snap in current.items()
            }
        )
        now = datetime.now(tz=UTC)
        healthy = folder.with_sync_state(
            sync_cursor=new_cursor,
            sync_status="healthy",
            last_error=None,
            imported_document_count=len(current),
            last_synchronized_at=now,
            now=now,
        )
        self._folders.save(healthy)
        self._config = ConnectorConfiguration(
            connector_id=CONNECTOR_FILESYSTEM,
            enabled=self._enabled,
            auth=AuthCredentialRef(method="none"),
            sync_cursor=new_cursor,
            options={"last_folder_id": folder.id},
        )

        return ConnectorResult.success_result(
            connector_id=CONNECTOR_FILESYSTEM,
            sync_mode=context.sync_mode,
            imported_count=imported,
            updated_count=updated,
            deleted_count=deleted,
            skipped_count=skipped,
            pending_changes=0,
            cursor=new_cursor,
            items=tuple(items),
            details={"folder_id": folder.id, "root_path": folder.root_path},
        )

    def _scan_folder(self, root: Path) -> dict[str, _FileSnapshot]:
        snapshots: dict[str, _FileSnapshot] = {}
        for path in sorted(root.rglob("*")):
            if not path.is_file():
                continue
            if path.suffix.lower() not in _SUPPORTED_EXTENSIONS:
                continue
            relative = PurePosixPath(path.relative_to(root).as_posix()).as_posix()
            if any(part.startswith(".") for part in PurePosixPath(relative).parts):
                continue
            stat = path.stat()
            content = path.read_bytes()
            digest = hashlib.sha256(content).hexdigest()
            modified_at = datetime.fromtimestamp(stat.st_mtime, tz=UTC)
            created_at = None
            if hasattr(stat, "st_ctime"):
                created_at = datetime.fromtimestamp(stat.st_ctime, tz=UTC)
            snapshots[relative] = _FileSnapshot(
                relative_path=relative,
                absolute_path=path,
                size=stat.st_size,
                mtime_ns=getattr(stat, "st_mtime_ns", int(stat.st_mtime * 1_000_000_000)),
                sha256=digest,
                content=content,
                created_at=created_at,
                modified_at=modified_at,
            )
        return snapshots

    def _build_item(
        self,
        *,
        folder: FilesystemFolderConnection,
        context: ConnectorExecutionContext,
        snapshot: _FileSnapshot | None,
        relative_path: str,
        change_kind: str,
        content: bytes,
    ) -> NormalizedImportItem:
        mime_type = _mime_for_path(relative_path)
        absolute = str((Path(folder.root_path) / relative_path).resolve())
        external_id = f"{folder.id}:{relative_path}"
        return NormalizedImportItem(
            name=PurePosixPath(relative_path).name,
            mime_type=mime_type,
            content=content,
            metadata=NormalizedSourceMetadata(
                connector_id=CONNECTOR_FILESYSTEM,
                external_id=external_id,
                workspace_id=context.workspace_id,
                source=f"filesystem://{folder.id}/{relative_path}",
                owner=None,
                created_at=snapshot.created_at if snapshot else None,
                modified_at=snapshot.modified_at if snapshot else None,
                tags=("filesystem", "connector"),
                extra={
                    "external_path": absolute,
                    "relative_path": relative_path,
                    "folder_id": folder.id,
                    "import_source": "filesystem",
                    "file_type": mime_type,
                },
            ),
            change_kind=change_kind,
        )


def _mime_for_path(relative_path: str) -> str:
    suffix = Path(relative_path).suffix.lower()
    if suffix in _EXTENSION_MIME_TYPES:
        return _EXTENSION_MIME_TYPES[suffix]
    guessed, _ = mimetypes.guess_type(relative_path)
    return guessed or "application/octet-stream"


def _encode_cursor(entries: dict[str, dict[str, object]]) -> str:
    return json.dumps({"entries": entries}, sort_keys=True, separators=(",", ":"))


def _decode_cursor(cursor: str | None) -> dict[str, dict[str, object]]:
    if not cursor:
        return {}
    try:
        payload = json.loads(cursor)
    except json.JSONDecodeError:
        return {}
    entries = payload.get("entries") if isinstance(payload, dict) else None
    if not isinstance(entries, dict):
        return {}
    result: dict[str, dict[str, object]] = {}
    for key, value in entries.items():
        if isinstance(key, str) and isinstance(value, dict):
            result[key] = value
    return result


def register_filesystem_connector(
    registry: object,
    *,
    document_import: DocumentImportPort | None = None,
    folders: FilesystemFolderRepository | None = None,
    enabled: bool = True,
) -> FilesystemConnector:
    """Register the Filesystem Connector on a ConnectorRegistry-like object."""
    connector = FilesystemConnector(
        document_import=document_import,
        folders=folders,
        enabled=enabled,
    )
    registry.register(connector)  # type: ignore[attr-defined]
    return connector
