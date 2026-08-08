"""Repository contract for filesystem folder connections."""

from typing import Protocol

from memovi_shared import WorkspaceId

from memovi_connectors.domain.entities import FilesystemFolderConnection


class FilesystemFolderRepository(Protocol):
    def get_by_id(
        self,
        folder_id: str,
        *,
        workspace_id: WorkspaceId,
    ) -> FilesystemFolderConnection | None:
        raise NotImplementedError

    def list_by_workspace(self, *, workspace_id: WorkspaceId) -> list[FilesystemFolderConnection]:
        raise NotImplementedError

    def add(self, folder: FilesystemFolderConnection) -> None:
        raise NotImplementedError

    def save(self, folder: FilesystemFolderConnection) -> None:
        raise NotImplementedError

    def delete(self, folder_id: str, *, workspace_id: WorkspaceId) -> None:
        raise NotImplementedError
