from dataclasses import dataclass

from memovi_shared import InvalidWorkspaceIdError, WorkspaceId

from memovi_workspace.application.dto import WorkspaceMembershipDto
from memovi_workspace.application.membership_guards import require_owner
from memovi_workspace.application.ports import UserDirectoryPort
from memovi_workspace.domain.entities.workspace_membership import (
    MEMBER_ROLE,
    OWNER_ROLE,
)
from memovi_workspace.domain.entities.workspace_membership_event import (
    WorkspaceMembershipEvent,
)
from memovi_workspace.domain.exceptions import (
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
class TransferWorkspaceOwnershipCommand:
    workspace_id: str
    actor_user_id: str
    new_owner_user_id: str


@dataclass(frozen=True, slots=True)
class TransferWorkspaceOwnershipResult:
    previous_owner: WorkspaceMembershipDto
    new_owner: WorkspaceMembershipDto


class TransferWorkspaceOwnership:
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

    def execute(
        self,
        command: TransferWorkspaceOwnershipCommand,
    ) -> TransferWorkspaceOwnershipResult:
        try:
            workspace_id = WorkspaceId(command.workspace_id)
        except InvalidWorkspaceIdError:
            raise
        if self._workspaces.get_by_id(workspace_id) is None:
            raise WorkspaceNotFoundError(f"Workspace '{command.workspace_id}' was not found.")

        actor = require_owner(
            self._memberships,
            user_id=command.actor_user_id,
            workspace_id=workspace_id,
        )
        if command.new_owner_user_id.strip() == command.actor_user_id.strip():
            raise WorkspaceMemberNotFoundError(
                "Select a different member to receive ownership.",
            )

        target = self._memberships.get(
            user_id=command.new_owner_user_id,
            workspace_id=workspace_id,
        )
        if target is None:
            raise WorkspaceMemberNotFoundError(
                f"User '{command.new_owner_user_id}' is not a member of this workspace.",
            )

        demoted = actor.with_role(MEMBER_ROLE)
        promoted = target.with_role(OWNER_ROLE)
        self._memberships.update(demoted)
        self._memberships.update(promoted)
        self._events.add(
            WorkspaceMembershipEvent.create(
                workspace_id=workspace_id,
                event_type="ownership_transferred",
                actor_user_id=command.actor_user_id,
                target_user_id=command.new_owner_user_id,
                detail="Ownership transferred",
            )
        )

        def email_for(user_id: str) -> str | None:
            if self._users is None:
                return None
            return self._users.find_email_by_user_id(user_id)

        return TransferWorkspaceOwnershipResult(
            previous_owner=WorkspaceMembershipDto.from_membership(
                demoted,
                email=email_for(demoted.user_id),
            ),
            new_owner=WorkspaceMembershipDto.from_membership(
                promoted,
                email=email_for(promoted.user_id),
            ),
        )
