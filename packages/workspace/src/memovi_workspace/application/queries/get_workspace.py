from dataclasses import dataclass

from memovi_shared import WorkspaceId

from memovi_workspace.application.dto import WorkspaceDto
from memovi_workspace.domain.exceptions import WorkspaceNotFoundError
from memovi_workspace.domain.repositories import WorkspaceRepository


@dataclass(frozen=True, slots=True)
class GetWorkspaceQuery:
    workspace_id: str


class GetWorkspace:
    def __init__(self, *, workspaces: WorkspaceRepository) -> None:
        self._workspaces = workspaces

    def execute(self, query: GetWorkspaceQuery) -> WorkspaceDto:
        workspace = self._workspaces.get_by_id(WorkspaceId(query.workspace_id))
        if workspace is None:
            raise WorkspaceNotFoundError(f"Workspace '{query.workspace_id}' was not found.")
        return WorkspaceDto.from_workspace(workspace)
