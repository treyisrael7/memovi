from dataclasses import dataclass

from memovi_workspace.application.dto import WorkspaceDto
from memovi_workspace.domain.entities import Workspace, WorkspaceMembership
from memovi_workspace.domain.repositories import (
    WorkspaceMembershipRepository,
    WorkspaceRepository,
)


@dataclass(frozen=True, slots=True)
class CreateWorkspaceCommand:
    name: str
    owner_user_id: str


@dataclass(frozen=True, slots=True)
class CreateWorkspaceResult:
    workspace: WorkspaceDto


class CreateWorkspace:
    def __init__(
        self,
        *,
        workspaces: WorkspaceRepository,
        memberships: WorkspaceMembershipRepository,
    ) -> None:
        self._workspaces = workspaces
        self._memberships = memberships

    def execute(self, command: CreateWorkspaceCommand) -> CreateWorkspaceResult:
        workspace = Workspace.create(name=command.name)
        self._workspaces.add(workspace)
        self._memberships.add(
            WorkspaceMembership.create(
                workspace_id=workspace.id,
                user_id=command.owner_user_id,
                role="owner",
            )
        )
        return CreateWorkspaceResult(workspace=WorkspaceDto.from_workspace(workspace))
