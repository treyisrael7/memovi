from dataclasses import dataclass
from datetime import datetime
from typing import Mapping, Sequence

from memovi_memory.domain.entities import Collection, CollectionMembership
from memovi_memory.domain.value_objects import (
    CollectionActivityEntry,
    CollectionMemberKind,
    CollectionSummary,
)


@dataclass(frozen=True, slots=True)
class CollectionDto:
    id: str
    workspace_id: str
    name: str
    description: str
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_collection(cls, collection: Collection) -> CollectionDto:
        return cls(
            id=collection.id.value,
            workspace_id=collection.workspace_id.value,
            name=collection.metadata.name,
            description=collection.metadata.description,
            created_at=collection.created_at,
            updated_at=collection.updated_at,
        )


@dataclass(frozen=True, slots=True)
class CollectionMembershipDto:
    id: str
    collection_id: str
    member_kind: str
    member_id: str
    reason: str
    added_at: datetime

    @classmethod
    def from_membership(cls, membership: CollectionMembership) -> CollectionMembershipDto:
        return cls(
            id=membership.id,
            collection_id=membership.collection_id.value,
            member_kind=membership.member_kind.value,
            member_id=membership.member_id,
            reason=membership.reason,
            added_at=membership.added_at,
        )


@dataclass(frozen=True, slots=True)
class CollectionActivityDto:
    activity_type: str
    occurred_at: datetime
    member_kind: str | None
    member_id: str | None
    detail: str

    @classmethod
    def from_entry(cls, entry: CollectionActivityEntry) -> CollectionActivityDto:
        return cls(
            activity_type=entry.activity_type,
            occurred_at=entry.occurred_at,
            member_kind=entry.member_kind.value if entry.member_kind else None,
            member_id=entry.member_id,
            detail=entry.detail,
        )


@dataclass(frozen=True, slots=True)
class CollectionSummaryDto:
    id: str
    workspace_id: str
    name: str
    description: str
    created_at: datetime
    updated_at: datetime
    item_count: int
    counts_by_kind: Mapping[str, int]
    recent_activity: Sequence[CollectionActivityDto]

    @classmethod
    def from_summary(cls, summary: CollectionSummary) -> CollectionSummaryDto:
        return cls(
            id=summary.id.value,
            workspace_id=summary.workspace_id.value,
            name=summary.metadata.name,
            description=summary.metadata.description,
            created_at=summary.created_at,
            updated_at=summary.updated_at,
            item_count=summary.item_count,
            counts_by_kind=dict(summary.counts_by_kind),
            recent_activity=tuple(
                CollectionActivityDto.from_entry(entry) for entry in summary.recent_activity
            ),
        )


@dataclass(frozen=True, slots=True)
class CollectionListItemDto:
    """Collection row with item counts for list views."""

    id: str
    workspace_id: str
    name: str
    description: str
    created_at: datetime
    updated_at: datetime
    item_count: int
    counts_by_kind: Mapping[str, int]

    @classmethod
    def from_collection_and_counts(
        cls,
        collection: Collection,
        *,
        counts_by_kind: Mapping[str, int],
    ) -> CollectionListItemDto:
        return cls(
            id=collection.id.value,
            workspace_id=collection.workspace_id.value,
            name=collection.metadata.name,
            description=collection.metadata.description,
            created_at=collection.created_at,
            updated_at=collection.updated_at,
            item_count=sum(counts_by_kind.values()),
            counts_by_kind=dict(counts_by_kind),
        )


def empty_counts() -> dict[str, int]:
    return {kind.value: 0 for kind in CollectionMemberKind}
