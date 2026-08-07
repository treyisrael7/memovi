from dataclasses import dataclass, replace
from datetime import UTC, datetime

from memovi_shared import WorkspaceId

from memovi_memory.domain.exceptions import InvalidCollectionError
from memovi_memory.domain.value_objects import CollectionId, CollectionMetadata


@dataclass(frozen=True, slots=True)
class Collection:
    """User-owned organizational grouping within a workspace.

    Collections organize references to Documents, Knowledge, Conversations, and
    Workflows. They do not store knowledge content or participate in ingestion.
    """

    id: CollectionId
    workspace_id: WorkspaceId
    metadata: CollectionMetadata
    created_at: datetime
    updated_at: datetime

    def __post_init__(self) -> None:
        if self.updated_at < self.created_at:
            raise InvalidCollectionError("Updated timestamp cannot precede created timestamp.")

    @classmethod
    def create(
        cls,
        *,
        workspace_id: WorkspaceId,
        name: str,
        description: str = "",
        collection_id: CollectionId | None = None,
        now: datetime | None = None,
    ) -> Collection:
        timestamp = now or datetime.now(UTC)
        return cls(
            id=collection_id or CollectionId.new(),
            workspace_id=workspace_id,
            metadata=CollectionMetadata(name=name, description=description),
            created_at=timestamp,
            updated_at=timestamp,
        )

    def rename(self, name: str, *, now: datetime | None = None) -> Collection:
        return replace(
            self,
            metadata=self.metadata.rename(name),
            updated_at=now or datetime.now(UTC),
        )

    def update_description(self, description: str, *, now: datetime | None = None) -> Collection:
        return replace(
            self,
            metadata=self.metadata.with_description(description),
            updated_at=now or datetime.now(UTC),
        )

    def touch(self, now: datetime | None = None) -> Collection:
        return replace(self, updated_at=now or datetime.now(UTC))
