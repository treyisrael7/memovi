from dataclasses import dataclass

from memovi_shared import WorkspaceId

from memovi_workspace.application.dto import WorkspaceDto
from memovi_workspace.domain.exceptions import (
    WorkspaceMembershipRequiredError,
    WorkspaceNotFoundError,
)
from memovi_workspace.domain.repositories import (
    WorkspaceMembershipRepository,
    WorkspaceRepository,
)


@dataclass(frozen=True, slots=True)
class GetWorkspaceQuery:
    workspace_id: str
    user_id: str


class GetWorkspace:
    def __init__(
        self,
        *,
        workspaces: WorkspaceRepository,
        memberships: WorkspaceMembershipRepository,
    ) -> None:
        self._workspaces = workspaces
        self._memberships = memberships

    def execute(self, query: GetWorkspaceQuery) -> WorkspaceDto:
        workspace_id = WorkspaceId(query.workspace_id)
        workspace = self._workspaces.get_by_id(workspace_id)
        if workspace is None:
            raise WorkspaceNotFoundError(f"Workspace '{query.workspace_id}' was not found.")
        membership = self._memberships.get(
            user_id=query.user_id,
            workspace_id=workspace_id,
        )
        if membership is None:
            raise WorkspaceMembershipRequiredError(
                f"User is not a member of workspace '{query.workspace_id}'.",
            )
        return WorkspaceDto.from_workspace(workspace, role=membership.role)
