from dataclasses import dataclass
from datetime import datetime

from memovi_workspace.domain.entities import Workspace
from memovi_workspace.domain.entities.workspace_membership import WorkspaceMembership
from memovi_workspace.domain.entities.workspace_membership_event import (
    WorkspaceMembershipEvent,
)


@dataclass(frozen=True, slots=True)
class WorkspaceDto:
    id: str
    name: str
    created_at: datetime
    role: str | None = None

    @classmethod
    def from_workspace(
        cls,
        workspace: Workspace,
        *,
        role: str | None = None,
    ) -> WorkspaceDto:
        return cls(
            id=workspace.id.value,
            name=workspace.name,
            created_at=workspace.created_at,
            role=role,
        )


@dataclass(frozen=True, slots=True)
class WorkspaceMembershipDto:
    id: str
    workspace_id: str
    user_id: str
    role: str
    created_at: datetime
    email: str | None = None

    @classmethod
    def from_membership(
        cls,
        membership: WorkspaceMembership,
        *,
        email: str | None = None,
    ) -> WorkspaceMembershipDto:
        return cls(
            id=membership.id,
            workspace_id=membership.workspace_id.value,
            user_id=membership.user_id,
            role=membership.role,
            created_at=membership.created_at,
            email=email,
        )


@dataclass(frozen=True, slots=True)
class WorkspaceMembershipEventDto:
    id: str
    workspace_id: str
    event_type: str
    actor_user_id: str
    target_user_id: str
    occurred_at: datetime
    detail: str

    @classmethod
    def from_event(cls, event: WorkspaceMembershipEvent) -> WorkspaceMembershipEventDto:
        return cls(
            id=event.id,
            workspace_id=event.workspace_id.value,
            event_type=event.event_type,
            actor_user_id=event.actor_user_id,
            target_user_id=event.target_user_id,
            occurred_at=event.occurred_at,
            detail=event.detail,
        )
