from dataclasses import dataclass

from memovi_shared import InvalidWorkspaceIdError, WorkspaceId

from memovi_workspace.application.dto import WorkspaceMembershipDto
from memovi_workspace.application.membership_guards import require_owner
from memovi_workspace.application.ports import UserDirectoryPort
from memovi_workspace.domain.entities.workspace_membership import (
    MEMBER_ROLE,
    WorkspaceMembership,
)
from memovi_workspace.domain.entities.workspace_membership_event import (
    WorkspaceMembershipEvent,
)
from memovi_workspace.domain.exceptions import (
    WorkspaceMemberAlreadyExistsError,
    WorkspaceNotFoundError,
    WorkspaceUserNotFoundError,
)
from memovi_workspace.domain.repositories import (
    WorkspaceMembershipRepository,
    WorkspaceRepository,
)
from memovi_workspace.domain.repositories.workspace_membership_event_repository import (
    WorkspaceMembershipEventRepository,
)


@dataclass(frozen=True, slots=True)
class InviteWorkspaceMemberCommand:
    workspace_id: str
    actor_user_id: str
    email: str


class InviteWorkspaceMember:
    def __init__(
        self,
        *,
        workspaces: WorkspaceRepository,
        memberships: WorkspaceMembershipRepository,
        events: WorkspaceMembershipEventRepository,
        users: UserDirectoryPort,
    ) -> None:
        self._workspaces = workspaces
        self._memberships = memberships
        self._events = events
        self._users = users

    def execute(self, command: InviteWorkspaceMemberCommand) -> WorkspaceMembershipDto:
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

        email = command.email.strip().lower()
        target_user_id = self._users.find_user_id_by_email(email)
        if target_user_id is None:
            raise WorkspaceUserNotFoundError(
                f"No registered user found for email '{email}'.",
            )

        existing = self._memberships.get(
            user_id=target_user_id,
            workspace_id=workspace_id,
        )
        if existing is not None:
            raise WorkspaceMemberAlreadyExistsError(
                f"User '{email}' is already a member of this workspace.",
            )

        membership = WorkspaceMembership.create(
            workspace_id=workspace_id,
            user_id=target_user_id,
            role=MEMBER_ROLE,
        )
        self._memberships.add(membership)
        self._events.add(
            WorkspaceMembershipEvent.create(
                workspace_id=workspace_id,
                event_type="member_invited",
                actor_user_id=command.actor_user_id,
                target_user_id=target_user_id,
                detail=f"Invited {email} as member",
            )
        )
        return WorkspaceMembershipDto.from_membership(membership, email=email)
