import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from memovi_shared import WorkspaceId

from memovi_memory.domain.exceptions import InvalidCollectionError
from memovi_memory.domain.value_objects import CollectionId, CollectionMemberKind


@dataclass(frozen=True, slots=True)
class CollectionActivity:
    """Durable activity entry for collection recent-activity views."""

    id: str
    collection_id: CollectionId
    workspace_id: WorkspaceId
    activity_type: str
    occurred_at: datetime
    member_kind: CollectionMemberKind | None = None
    member_id: str | None = None
    detail: str = ""

    def __post_init__(self) -> None:
        activity_type = self.activity_type.strip()
        if not activity_type:
            raise InvalidCollectionError("Activity type is required.")
        object.__setattr__(self, "activity_type", activity_type)
        object.__setattr__(self, "detail", self.detail.strip())
        try:
            uuid.UUID(self.id)
        except ValueError as exc:
            raise InvalidCollectionError("Activity ID must be a valid UUID.") from exc

    @classmethod
    def create(
        cls,
        *,
        collection_id: CollectionId,
        workspace_id: WorkspaceId,
        activity_type: str,
        member_kind: CollectionMemberKind | None = None,
        member_id: str | None = None,
        detail: str = "",
        activity_id: str | None = None,
        now: datetime | None = None,
    ) -> CollectionActivity:
        return cls(
            id=activity_id or str(uuid.uuid4()),
            collection_id=collection_id,
            workspace_id=workspace_id,
            activity_type=activity_type,
            occurred_at=now or datetime.now(UTC),
            member_kind=member_kind,
            member_id=member_id,
            detail=detail,
        )
