from dataclasses import dataclass

from memovi_shared import InvalidWorkspaceIdError, WorkspaceId

from memovi_workspace.application.dto import WorkspaceMembershipDto
from memovi_workspace.application.membership_guards import require_owner
from memovi_workspace.application.ports import UserDirectoryPort
from memovi_workspace.domain.entities.workspace_membership import OWNER_ROLE
from memovi_workspace.domain.entities.workspace_membership_event import (
    WorkspaceMembershipEvent,
)
from memovi_workspace.domain.exceptions import (
    CannotRemoveLastOwnerError,
    WorkspaceMemberNotFoundError,
    WorkspaceNotFoundError,
)
from memovi_workspace.domain.repositories import (
    WorkspaceMembershipRepository,
    WorkspaceRepository,
)
from memovi_workspace.domain.repositories.workspace_membership_event_repository import (
    WorkspaceMembershipEventRepository,
)


@dataclass(frozen=True, slots=True)
class RemoveWorkspaceMemberCommand:
    workspace_id: str
    actor_user_id: str
    target_user_id: str


class RemoveWorkspaceMember:
    def __init__(
        self,
        *,
        workspaces: WorkspaceRepository,
        memberships: WorkspaceMembershipRepository,
        events: WorkspaceMembershipEventRepository,
        users: UserDirectoryPort | None = None,
    ) -> None:
        self._workspaces = workspaces
        self._memberships = memberships
        self._events = events
        self._users = users

    def execute(self, command: RemoveWorkspaceMemberCommand) -> WorkspaceMembershipDto:
        try:
            workspace_id = WorkspaceId(command.workspace_id)
        except InvalidWorkspaceIdError:
            raise
        if self._workspaces.get_by_id(workspace_id) is None:
            raise WorkspaceNotFoundError(f"Workspace '{command.workspace_id}' was not found.")

        require_owner(
            self._memberships,
            user_id=command.actor_user_id,
            workspace_id=workspace_id,
        )

        target = self._memberships.get(
            user_id=command.target_user_id,
            workspace_id=workspace_id,
        )
        if target is None:
            raise WorkspaceMemberNotFoundError(
                f"User '{command.target_user_id}' is not a member of this workspace.",
            )

        if target.role == OWNER_ROLE:
            owner_count = self._memberships.count_by_role(
                workspace_id=workspace_id,
                role=OWNER_ROLE,
            )
            if owner_count <= 1:
                raise CannotRemoveLastOwnerError(
                    "Cannot remove the last owner. Transfer ownership first.",
                )

        removed = self._memberships.remove(
            user_id=command.target_user_id,
            workspace_id=workspace_id,
        )
        assert removed is not None
        self._events.add(
            WorkspaceMembershipEvent.create(
                workspace_id=workspace_id,
                event_type="member_removed",
                actor_user_id=command.actor_user_id,
                target_user_id=command.target_user_id,
                detail="Member removed by owner",
            )
        )
        email = (
            self._users.find_email_by_user_id(removed.user_id) if self._users is not None else None
        )
        return WorkspaceMembershipDto.from_membership(removed, email=email)
