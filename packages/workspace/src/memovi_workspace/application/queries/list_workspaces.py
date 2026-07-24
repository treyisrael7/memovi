from memovi_workspace.application.dto import WorkspaceDto
from memovi_workspace.domain.repositories import WorkspaceRepository


class ListWorkspaces:
    def __init__(self, *, workspaces: WorkspaceRepository) -> None:
        self._workspaces = workspaces

    def execute(self) -> list[WorkspaceDto]:
        return [WorkspaceDto.from_workspace(workspace) for workspace in self._workspaces.list_all()]
