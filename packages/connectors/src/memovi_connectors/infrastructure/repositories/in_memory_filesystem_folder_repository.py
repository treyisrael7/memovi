"""In-memory filesystem folder repository for unit tests."""

from __future__ import annotations

from memovi_shared import WorkspaceId

from memovi_connectors.domain.entities import FilesystemFolderConnection


class InMemoryFilesystemFolderRepository:
    def __init__(self) -> None:
        self.folders: dict[str, FilesystemFolderConnection] = {}

    def get_by_id(
        self,
        folder_id: str,
        *,
        workspace_id: WorkspaceId,
    ) -> FilesystemFolderConnection | None:
        folder = self.folders.get(folder_id)
        if folder is None or folder.workspace_id != workspace_id:
            return None
        return folder

    def list_by_workspace(self, *, workspace_id: WorkspaceId) -> list[FilesystemFolderConnection]:
        return [folder for folder in self.folders.values() if folder.workspace_id == workspace_id]

    def add(self, folder: FilesystemFolderConnection) -> None:
        self.folders[folder.id] = folder

    def save(self, folder: FilesystemFolderConnection) -> None:
        self.folders[folder.id] = folder

    def delete(self, folder_id: str, *, workspace_id: WorkspaceId) -> None:
        folder = self.folders.get(folder_id)
        if folder is not None and folder.workspace_id == workspace_id:
            del self.folders[folder_id]
