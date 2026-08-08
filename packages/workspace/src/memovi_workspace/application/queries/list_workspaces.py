from dataclasses import dataclass

from memovi_workspace.application.dto import WorkspaceDto
from memovi_workspace.domain.repositories import (
    WorkspaceMembershipRepository,
    WorkspaceRepository,
)


@dataclass(frozen=True, slots=True)
class ListWorkspacesQuery:
    user_id: str


class ListWorkspaces:
    def __init__(
        self,
        *,
        workspaces: WorkspaceRepository,
        memberships: WorkspaceMembershipRepository,
    ) -> None:
        self._workspaces = workspaces
        self._memberships = memberships

    def execute(self, query: ListWorkspacesQuery | None = None) -> list[WorkspaceDto]:
        if query is None:
            return [
                WorkspaceDto.from_workspace(workspace) for workspace in self._workspaces.list_all()
            ]
        memberships = self._memberships.list_for_user(query.user_id)
        results: list[WorkspaceDto] = []
        for membership in memberships:
            workspace = self._workspaces.get_by_id(membership.workspace_id)
            if workspace is not None:
                results.append(
                    WorkspaceDto.from_workspace(workspace, role=membership.role),
                )
        return results
