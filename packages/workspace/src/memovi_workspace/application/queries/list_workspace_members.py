from dataclasses import dataclass

from memovi_shared import InvalidWorkspaceIdError, WorkspaceId

from memovi_workspace.application.dto import WorkspaceMembershipDto
from memovi_workspace.application.membership_guards import require_membership
from memovi_workspace.application.ports import UserDirectoryPort
from memovi_workspace.domain.exceptions import WorkspaceNotFoundError
from memovi_workspace.domain.repositories import (
    WorkspaceMembershipRepository,
    WorkspaceRepository,
)


@dataclass(frozen=True, slots=True)
class ListWorkspaceMembersQuery:
    workspace_id: str
    actor_user_id: str


class ListWorkspaceMembers:
    def __init__(
        self,
        *,
        workspaces: WorkspaceRepository,
        memberships: WorkspaceMembershipRepository,
        users: UserDirectoryPort | None = None,
    ) -> None:
        self._workspaces = workspaces
        self._memberships = memberships
        self._users = users

    def execute(self, query: ListWorkspaceMembersQuery) -> list[WorkspaceMembershipDto]:
        try:
            workspace_id = WorkspaceId(query.workspace_id)
        except InvalidWorkspaceIdError:
            raise
        if self._workspaces.get_by_id(workspace_id) is None:
            raise WorkspaceNotFoundError(f"Workspace '{query.workspace_id}' was not found.")

        require_membership(
            self._memberships,
            user_id=query.actor_user_id,
            workspace_id=workspace_id,
        )
        members = self._memberships.list_for_workspace(workspace_id)
        results: list[WorkspaceMembershipDto] = []
        for membership in members:
            email = (
                self._users.find_email_by_user_id(membership.user_id)
                if self._users is not None
                else None
            )
            results.append(WorkspaceMembershipDto.from_membership(membership, email=email))
        return results
