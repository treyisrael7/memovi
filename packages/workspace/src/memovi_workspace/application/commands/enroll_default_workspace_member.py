from dataclasses import dataclass

from memovi_shared import DEFAULT_WORKSPACE_ID

from memovi_workspace.domain.entities import WorkspaceMembership
from memovi_workspace.domain.entities.workspace_membership import MEMBER_ROLE, OWNER_ROLE
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
        # Default Workspace is seeded without an owner. The first registered
        # user becomes owner so owner-only settings (capability permission
        # modes) work on the V1 fallback workspace. Later users stay members.
        owners = self._memberships.count_by_role(
            workspace_id=workspace.id,
            role=OWNER_ROLE,
        )
        role = OWNER_ROLE if owners == 0 else MEMBER_ROLE
        self._memberships.add(
            WorkspaceMembership.create(
                workspace_id=workspace.id,
                user_id=command.user_id,
                role=role,
            )
        )
