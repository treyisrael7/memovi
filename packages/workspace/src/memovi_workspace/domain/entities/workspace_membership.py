from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

from memovi_shared import WorkspaceId

from memovi_workspace.domain.exceptions import WorkspaceDomainError

VALID_ROLES = frozenset({"owner", "member"})


class InvalidWorkspaceMembershipError(WorkspaceDomainError):
    """Raised when membership fields violate invariants."""


@dataclass(frozen=True, slots=True)
class WorkspaceMembership:
    """Association between an authenticated user and a workspace."""

    id: str
    workspace_id: WorkspaceId
    user_id: str
    role: str
    created_at: datetime

    def __post_init__(self) -> None:
        if not self.id.strip():
            raise InvalidWorkspaceMembershipError("Membership id is required.")
        user_id = self.user_id.strip()
        if not user_id:
            raise InvalidWorkspaceMembershipError("Membership user_id is required.")
        role = self.role.strip().lower()
        if role not in VALID_ROLES:
            raise InvalidWorkspaceMembershipError(
                f"Membership role must be one of {sorted(VALID_ROLES)}.",
            )
        object.__setattr__(self, "id", self.id.strip())
        object.__setattr__(self, "user_id", user_id)
        object.__setattr__(self, "role", role)

    @classmethod
    def create(
        cls,
        *,
        workspace_id: WorkspaceId,
        user_id: str,
        role: str = "member",
        membership_id: str | None = None,
        now: datetime | None = None,
    ) -> WorkspaceMembership:
        return cls(
            id=membership_id or str(uuid4()),
            workspace_id=workspace_id,
            user_id=user_id,
            role=role,
            created_at=now or datetime.now(UTC),
        )
