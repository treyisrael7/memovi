from dataclasses import dataclass

from memovi_shared import DEFAULT_WORKSPACE_ID

from memovi_workspace.domain.entities import WorkspaceMembership
from memovi_workspace.domain.repositories import (
    WorkspaceMembershipRepository,
    WorkspaceRepository,
)


@dataclass(frozen=True, slots=True)
class EnrollDefaultWorkspaceMemberCommand:
    user_id: str


class EnrollDefaultWorkspaceMember:
    """Ensure a newly registered user can access the seeded Default Workspace."""

    def __init__(
        self,
        *,
        workspaces: WorkspaceRepository,
        memberships: WorkspaceMembershipRepository,
    ) -> None:
        self._workspaces = workspaces
        self._memberships = memberships

    def execute(self, command: EnrollDefaultWorkspaceMemberCommand) -> None:
        workspace = self._workspaces.get_by_id(DEFAULT_WORKSPACE_ID)
        if workspace is None:
            return
        self._memberships.add(
            WorkspaceMembership.create(
                workspace_id=workspace.id,
                user_id=command.user_id,
                role="member",
            )
        )
