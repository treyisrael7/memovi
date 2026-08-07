from dataclasses import dataclass
from datetime import datetime
from typing import Mapping, Sequence

from memovi_shared import WorkspaceId

from memovi_memory.domain.value_objects.collection_id import CollectionId
from memovi_memory.domain.value_objects.collection_metadata import CollectionMetadata
from memovi_memory.domain.value_objects.collection_member_kind import CollectionMemberKind


@dataclass(frozen=True, slots=True)
class CollectionActivityEntry:
    """A single organizational event for collection recent-activity views."""

    activity_type: str
    occurred_at: datetime
    member_kind: CollectionMemberKind | None = None
    member_id: str | None = None
    detail: str = ""


@dataclass(frozen=True, slots=True)
class CollectionSummary:
    """Read model for collection statistics and recent activity."""

    id: CollectionId
    workspace_id: WorkspaceId
    metadata: CollectionMetadata
    created_at: datetime
    updated_at: datetime
    item_count: int
    counts_by_kind: Mapping[str, int]
    recent_activity: Sequence[CollectionActivityEntry]
