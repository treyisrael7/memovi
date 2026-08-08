"""Application service for registering and syncing filesystem folders."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from memovi_shared import WorkspaceId

from memovi_connectors.application.ports import Connector
from memovi_connectors.application.services.connector_scheduler import ConnectorScheduler
from memovi_connectors.domain.entities import FilesystemFolderConnection
from memovi_connectors.domain.exceptions import InvalidConnectorError, UnknownConnectorError
from memovi_connectors.domain.repositories import FilesystemFolderRepository
from memovi_connectors.domain.value_objects import (
    CONNECTOR_FILESYSTEM,
    ConnectorExecutionContext,
    ConnectorResult,
)


@dataclass(frozen=True, slots=True)
class AddFilesystemFolderCommand:
    workspace_id: WorkspaceId
    root_path: str
    display_name: str | None = None


@dataclass(frozen=True, slots=True)
class SyncFilesystemFolderCommand:
    workspace_id: WorkspaceId
    folder_id: str
    sync_mode: str | None = None


class FilesystemFolderService:
    """Owns folder registration and on-demand sync for the Filesystem Connector."""

    def __init__(
        self,
        *,
        folders: FilesystemFolderRepository,
        scheduler: ConnectorScheduler,
        connector: Connector | None = None,
    ) -> None:
        self._folders = folders
        self._scheduler = scheduler
        self._connector = connector

    def list_folders(self, *, workspace_id: WorkspaceId) -> list[FilesystemFolderConnection]:
        return self._folders.list_by_workspace(workspace_id=workspace_id)

    def get_folder(
        self,
        *,
        workspace_id: WorkspaceId,
        folder_id: str,
    ) -> FilesystemFolderConnection | None:
        return self._folders.get_by_id(folder_id, workspace_id=workspace_id)

    def add_folder(self, command: AddFilesystemFolderCommand) -> FilesystemFolderConnection:
        root = Path(command.root_path).expanduser()
        try:
            resolved = root.resolve(strict=False)
        except OSError as exc:
            raise InvalidConnectorError(f"Invalid folder path: {exc}") from exc
        if not resolved.exists() or not resolved.is_dir():
            raise InvalidConnectorError(
                f"Folder path does not exist or is not a directory: {resolved}",
            )

        existing = self._folders.list_by_workspace(workspace_id=command.workspace_id)
        normalized = str(resolved)
        for folder in existing:
            if Path(folder.root_path).resolve(strict=False) == resolved:
                raise InvalidConnectorError(
                    f"Folder is already connected in this workspace: {normalized}",
                )

        folder = FilesystemFolderConnection.create(
            workspace_id=command.workspace_id,
            root_path=normalized,
            display_name=command.display_name,
        )
        self._folders.add(folder)
        return folder

    def remove_folder(self, *, workspace_id: WorkspaceId, folder_id: str) -> None:
        folder = self._folders.get_by_id(folder_id, workspace_id=workspace_id)
        if folder is None:
            raise UnknownConnectorError(f"Filesystem folder '{folder_id}' was not found.")
        self._folders.delete(folder_id, workspace_id=workspace_id)

    def sync_folder(self, command: SyncFilesystemFolderCommand) -> ConnectorResult:
        folder = self._folders.get_by_id(command.folder_id, workspace_id=command.workspace_id)
        if folder is None:
            raise UnknownConnectorError(
                f"Filesystem folder '{command.folder_id}' was not found.",
            )

        sync_mode = command.sync_mode
        if sync_mode is None:
            sync_mode = "incremental" if folder.sync_cursor else "initial"

        context = ConnectorExecutionContext.create(
            workspace_id=command.workspace_id,
            connector_id=CONNECTOR_FILESYSTEM,
            sync_mode=sync_mode,
            cursor=folder.sync_cursor,
            metadata={"folder_id": folder.id, "root_path": folder.root_path},
        )
        return self._scheduler.run_now(connector_id=CONNECTOR_FILESYSTEM, context=context)
