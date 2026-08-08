from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

from memovi_shared import WorkspaceId

from memovi_workspace.domain.exceptions import WorkspaceDomainError

MEMBERSHIP_EVENT_TYPES = frozenset(
    {
        "member_invited",
        "member_removed",
        "ownership_transferred",
        "member_left",
    }
)


class InvalidWorkspaceMembershipEventError(WorkspaceDomainError):
    """Raised when a membership audit event violates invariants."""


@dataclass(frozen=True, slots=True)
class WorkspaceMembershipEvent:
    """Durable audit entry for workspace membership changes."""

    id: str
    workspace_id: WorkspaceId
    event_type: str
    actor_user_id: str
    target_user_id: str
    occurred_at: datetime
    detail: str = ""

    def __post_init__(self) -> None:
        event_type = self.event_type.strip().lower()
        if event_type not in MEMBERSHIP_EVENT_TYPES:
            raise InvalidWorkspaceMembershipEventError(
                f"Event type must be one of {sorted(MEMBERSHIP_EVENT_TYPES)}.",
            )
        actor = self.actor_user_id.strip()
        target = self.target_user_id.strip()
        if not actor:
            raise InvalidWorkspaceMembershipEventError("Actor user id is required.")
        if not target:
            raise InvalidWorkspaceMembershipEventError("Target user id is required.")
        object.__setattr__(self, "event_type", event_type)
        object.__setattr__(self, "actor_user_id", actor)
        object.__setattr__(self, "target_user_id", target)
        object.__setattr__(self, "detail", self.detail.strip())

    @classmethod
    def create(
        cls,
        *,
        workspace_id: WorkspaceId,
        event_type: str,
        actor_user_id: str,
        target_user_id: str,
        detail: str = "",
        event_id: str | None = None,
        now: datetime | None = None,
    ) -> WorkspaceMembershipEvent:
        return cls(
            id=event_id or str(uuid4()),
            workspace_id=workspace_id,
            event_type=event_type,
            actor_user_id=actor_user_id,
            target_user_id=target_user_id,
            occurred_at=now or datetime.now(UTC),
            detail=detail,
        )
