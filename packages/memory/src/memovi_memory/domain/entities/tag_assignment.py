import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from memovi_memory.domain.exceptions import InvalidTagAssignmentError
from memovi_memory.domain.value_objects import CollectionMemberKind, TagId

_MAX_MEMBER_ID_LENGTH = 256


@dataclass(frozen=True, slots=True)
class TagAssignment:
    """Assignment of a platform resource to a tag.

    Assignments are organizational references only. The referenced resource
    remains owned by its domain. Deleting a tag removes assignments without
    touching underlying content.
    """

    id: str
    tag_id: TagId
    member_kind: CollectionMemberKind
    member_id: str
    assigned_at: datetime

    def __post_init__(self) -> None:
        member_id = self.member_id.strip()
        if not member_id:
            raise InvalidTagAssignmentError("Member ID is required.")
        if len(member_id) > _MAX_MEMBER_ID_LENGTH:
            raise InvalidTagAssignmentError(
                f"Member ID must be at most {_MAX_MEMBER_ID_LENGTH} characters.",
            )
        object.__setattr__(self, "member_id", member_id)

        try:
            uuid.UUID(self.id)
        except ValueError as exc:
            raise InvalidTagAssignmentError("Assignment ID must be a valid UUID.") from exc

    @classmethod
    def create(
        cls,
        *,
        tag_id: TagId,
        member_kind: CollectionMemberKind,
        member_id: str,
        assignment_id: str | None = None,
        now: datetime | None = None,
    ) -> TagAssignment:
        return cls(
            id=assignment_id or str(uuid.uuid4()),
            tag_id=tag_id,
            member_kind=member_kind,
            member_id=member_id,
            assigned_at=now or datetime.now(UTC),
        )
