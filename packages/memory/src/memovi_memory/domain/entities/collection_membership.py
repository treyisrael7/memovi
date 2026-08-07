import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from memovi_memory.domain.exceptions import InvalidCollectionMembershipError
from memovi_memory.domain.value_objects import CollectionId, CollectionMemberKind

_MAX_REASON_LENGTH = 500
_MAX_MEMBER_ID_LENGTH = 256


@dataclass(frozen=True, slots=True)
class CollectionMembership:
    """Membership of a platform resource in a collection.

    Memberships are organizational references only. The referenced resource
    remains owned by its domain (Documents, Memory, Intelligence, Automation).
    ``reason`` explains why the item appears in the collection.
    """

    id: str
    collection_id: CollectionId
    member_kind: CollectionMemberKind
    member_id: str
    reason: str
    added_at: datetime

    def __post_init__(self) -> None:
        member_id = self.member_id.strip()
        if not member_id:
            raise InvalidCollectionMembershipError("Member ID is required.")
        if len(member_id) > _MAX_MEMBER_ID_LENGTH:
            raise InvalidCollectionMembershipError(
                f"Member ID must be at most {_MAX_MEMBER_ID_LENGTH} characters.",
            )
        reason = self.reason.strip() or "Added by user"
        if len(reason) > _MAX_REASON_LENGTH:
            raise InvalidCollectionMembershipError(
                f"Membership reason must be at most {_MAX_REASON_LENGTH} characters.",
            )
        object.__setattr__(self, "member_id", member_id)
        object.__setattr__(self, "reason", reason)

        try:
            uuid.UUID(self.id)
        except ValueError as exc:
            raise InvalidCollectionMembershipError(
                "Membership ID must be a valid UUID.",
            ) from exc

    @classmethod
    def create(
        cls,
        *,
        collection_id: CollectionId,
        member_kind: CollectionMemberKind,
        member_id: str,
        reason: str = "Added by user",
        membership_id: str | None = None,
        now: datetime | None = None,
    ) -> CollectionMembership:
        return cls(
            id=membership_id or str(uuid.uuid4()),
            collection_id=collection_id,
            member_kind=member_kind,
            member_id=member_id,
            reason=reason,
            added_at=now or datetime.now(UTC),
        )
