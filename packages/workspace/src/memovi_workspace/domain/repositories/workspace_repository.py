from typing import Protocol

from memovi_shared import WorkspaceId

from memovi_workspace.domain.entities import Workspace


class WorkspaceRepository(Protocol):
    """Persistence contract for workspace ownership boundaries."""

    def get_by_id(self, workspace_id: WorkspaceId) -> Workspace | None:
        raise NotImplementedError

    def add(self, workspace: Workspace) -> None:
        raise NotImplementedError

    def list_all(self) -> list[Workspace]:
        raise NotImplementedError
