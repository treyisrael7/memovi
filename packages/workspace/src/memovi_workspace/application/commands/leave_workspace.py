from dataclasses import dataclass

from memovi_shared import InvalidWorkspaceIdError, WorkspaceId

from memovi_workspace.application.dto import WorkspaceMembershipDto
from memovi_workspace.application.membership_guards import require_membership
from memovi_workspace.application.ports import UserDirectoryPort
from memovi_workspace.domain.entities.workspace_membership import OWNER_ROLE
from memovi_workspace.domain.entities.workspace_membership_event import (
    WorkspaceMembershipEvent,
)
from memovi_workspace.domain.exceptions import (
    CannotLeaveAsSoleOwnerError,
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
class LeaveWorkspaceCommand:
    workspace_id: str
    user_id: str


class LeaveWorkspace:
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

    def execute(self, command: LeaveWorkspaceCommand) -> WorkspaceMembershipDto:
        try:
            workspace_id = WorkspaceId(command.workspace_id)
        except InvalidWorkspaceIdError:
            raise
        if self._workspaces.get_by_id(workspace_id) is None:
            raise WorkspaceNotFoundError(f"Workspace '{command.workspace_id}' was not found.")

        membership = require_membership(
            self._memberships,
            user_id=command.user_id,
            workspace_id=workspace_id,
        )
        if membership.role == OWNER_ROLE:
            owner_count = self._memberships.count_by_role(
                workspace_id=workspace_id,
                role=OWNER_ROLE,
            )
            if owner_count <= 1:
                raise CannotLeaveAsSoleOwnerError(
                    "Transfer ownership before leaving as the sole owner.",
                )

        removed = self._memberships.remove(
            user_id=command.user_id,
            workspace_id=workspace_id,
        )
        assert removed is not None
        self._events.add(
            WorkspaceMembershipEvent.create(
                workspace_id=workspace_id,
                event_type="member_left",
                actor_user_id=command.user_id,
                target_user_id=command.user_id,
                detail="Member left the workspace",
            )
        )
        email = (
            self._users.find_email_by_user_id(removed.user_id) if self._users is not None else None
        )
        return WorkspaceMembershipDto.from_membership(removed, email=email)
