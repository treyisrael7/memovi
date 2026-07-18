from dataclasses import dataclass

from memovi_workspace.application.dto import WorkspaceDto
from memovi_workspace.domain.entities import Workspace
from memovi_workspace.domain.repositories import WorkspaceRepository


@dataclass(frozen=True, slots=True)
class CreateWorkspaceCommand:
    name: str


@dataclass(frozen=True, slots=True)
class CreateWorkspaceResult:
    workspace: WorkspaceDto


class CreateWorkspace:
    def __init__(self, *, workspaces: WorkspaceRepository) -> None:
        self._workspaces = workspaces

    def execute(self, command: CreateWorkspaceCommand) -> CreateWorkspaceResult:
        workspace = Workspace.create(name=command.name)
        self._workspaces.add(workspace)
        return CreateWorkspaceResult(workspace=WorkspaceDto.from_workspace(workspace))
