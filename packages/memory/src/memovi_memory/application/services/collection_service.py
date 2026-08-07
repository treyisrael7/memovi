from collections.abc import Callable, Sequence
from datetime import UTC, datetime

from memovi_shared import WorkspaceId

from memovi_memory.application.dto.collection_dto import (
    CollectionDto,
    CollectionListItemDto,
    CollectionMembershipDto,
    CollectionSummaryDto,
    empty_counts,
)
from memovi_memory.domain.entities import Collection, CollectionActivity, CollectionMembership
from memovi_memory.domain.events import (
    CollectionCreated,
    CollectionDeleted,
    CollectionMemberAdded,
    CollectionMemberRemoved,
    CollectionUpdated,
)
from memovi_memory.domain.exceptions import (
    CollectionMembershipNotFoundError,
    CollectionNotFoundError,
    DuplicateCollectionMembershipError,
    InvalidCollectionIdError,
)
from memovi_memory.domain.repositories import CollectionRepository
from memovi_memory.domain.value_objects import (
    CollectionActivityEntry,
    CollectionId,
    CollectionMemberKind,
    CollectionSummary,
    parse_member_kind,
)

EventPublisher = Callable[[object], None]


class CollectionService:
    """Application service for knowledge organization via collections."""

    def __init__(
        self,
        *,
        repository: CollectionRepository,
        publish: EventPublisher | None = None,
    ) -> None:
        self._repository = repository
        self._publish = publish

    def create(
        self,
        *,
        workspace_id: WorkspaceId,
        name: str,
        description: str = "",
        now: datetime | None = None,
    ) -> CollectionDto:
        timestamp = now or datetime.now(UTC)
        collection = Collection.create(
            workspace_id=workspace_id,
            name=name,
            description=description,
            now=timestamp,
        )
        self._repository.add(collection)
        self._repository.add_activity(
            CollectionActivity.create(
                collection_id=collection.id,
                workspace_id=workspace_id,
                activity_type="created",
                detail=f"Created collection “{collection.metadata.name}”",
                now=timestamp,
            )
        )
        self._emit(
            CollectionCreated(
                collection_id=collection.id.value,
                workspace_id=workspace_id,
                name=collection.metadata.name,
                occurred_at=timestamp,
            )
        )
        return CollectionDto.from_collection(collection)

    def rename(
        self,
        collection_id: str,
        *,
        workspace_id: WorkspaceId,
        name: str,
        now: datetime | None = None,
    ) -> CollectionDto:
        collection = self._require_collection(collection_id, workspace_id=workspace_id)
        timestamp = now or datetime.now(UTC)
        updated = collection.rename(name, now=timestamp)
        self._repository.save(updated)
        self._repository.add_activity(
            CollectionActivity.create(
                collection_id=updated.id,
                workspace_id=workspace_id,
                activity_type="renamed",
                detail=f"Renamed to “{updated.metadata.name}”",
                now=timestamp,
            )
        )
        self._emit(
            CollectionUpdated(
                collection_id=updated.id.value,
                workspace_id=workspace_id,
                name=updated.metadata.name,
                occurred_at=timestamp,
            )
        )
        return CollectionDto.from_collection(updated)

    def update_description(
        self,
        collection_id: str,
        *,
        workspace_id: WorkspaceId,
        description: str,
        now: datetime | None = None,
    ) -> CollectionDto:
        collection = self._require_collection(collection_id, workspace_id=workspace_id)
        timestamp = now or datetime.now(UTC)
        updated = collection.update_description(description, now=timestamp)
        self._repository.save(updated)
        self._repository.add_activity(
            CollectionActivity.create(
                collection_id=updated.id,
                workspace_id=workspace_id,
                activity_type="description_updated",
                detail="Updated collection description",
                now=timestamp,
            )
        )
        self._emit(
            CollectionUpdated(
                collection_id=updated.id.value,
                workspace_id=workspace_id,
                name=updated.metadata.name,
                occurred_at=timestamp,
            )
        )
        return CollectionDto.from_collection(updated)

    def delete(
        self,
        collection_id: str,
        *,
        workspace_id: WorkspaceId,
        now: datetime | None = None,
    ) -> None:
        collection = self._require_collection(collection_id, workspace_id=workspace_id)
        deleted = self._repository.delete(collection.id, workspace_id=workspace_id)
        if not deleted:
            raise CollectionNotFoundError(f"Collection {collection_id} was not found.")
        timestamp = now or datetime.now(UTC)
        self._emit(
            CollectionDeleted(
                collection_id=collection.id.value,
                workspace_id=workspace_id,
                occurred_at=timestamp,
            )
        )

    def get(
        self,
        collection_id: str,
        *,
        workspace_id: WorkspaceId,
    ) -> CollectionDto:
        return CollectionDto.from_collection(
            self._require_collection(collection_id, workspace_id=workspace_id)
        )

    def list(
        self,
        *,
        workspace_id: WorkspaceId,
    ) -> Sequence[CollectionListItemDto]:
        collections = self._repository.list_by_workspace(workspace_id=workspace_id)
        items: list[CollectionListItemDto] = []
        for collection in collections:
            counts = empty_counts()
            counts.update(
                self._repository.count_memberships_by_kind(
                    collection.id,
                    workspace_id=workspace_id,
                )
            )
            items.append(
                CollectionListItemDto.from_collection_and_counts(
                    collection,
                    counts_by_kind=counts,
                )
            )
        return items

    def summary(
        self,
        collection_id: str,
        *,
        workspace_id: WorkspaceId,
        activity_limit: int = 20,
    ) -> CollectionSummaryDto:
        collection = self._require_collection(collection_id, workspace_id=workspace_id)
        counts = empty_counts()
        counts.update(
            self._repository.count_memberships_by_kind(
                collection.id,
                workspace_id=workspace_id,
            )
        )
        activities = self._repository.list_recent_activity(
            collection.id,
            workspace_id=workspace_id,
            limit=activity_limit,
        )
        summary = CollectionSummary(
            id=collection.id,
            workspace_id=workspace_id,
            metadata=collection.metadata,
            created_at=collection.created_at,
            updated_at=collection.updated_at,
            item_count=sum(counts.values()),
            counts_by_kind=counts,
            recent_activity=tuple(
                CollectionActivityEntry(
                    activity_type=activity.activity_type,
                    occurred_at=activity.occurred_at,
                    member_kind=activity.member_kind,
                    member_id=activity.member_id,
                    detail=activity.detail,
                )
                for activity in activities
            ),
        )
        return CollectionSummaryDto.from_summary(summary)

    def list_members(
        self,
        collection_id: str,
        *,
        workspace_id: WorkspaceId,
        member_kind: str | None = None,
        query: str | None = None,
    ) -> Sequence[CollectionMembershipDto]:
        collection = self._require_collection(collection_id, workspace_id=workspace_id)
        kind = parse_member_kind(member_kind) if member_kind else None
        memberships = self._repository.list_memberships(
            collection.id,
            workspace_id=workspace_id,
            member_kind=kind,
            query=query,
        )
        return tuple(CollectionMembershipDto.from_membership(item) for item in memberships)

    def add_member(
        self,
        collection_id: str,
        *,
        workspace_id: WorkspaceId,
        member_kind: str,
        member_id: str,
        reason: str = "Added by user",
        now: datetime | None = None,
    ) -> CollectionMembershipDto:
        collection = self._require_collection(collection_id, workspace_id=workspace_id)
        kind = parse_member_kind(member_kind)
        existing = self._repository.get_membership(
            collection_id=collection.id,
            member_kind=kind,
            member_id=member_id.strip(),
            workspace_id=workspace_id,
        )
        if existing is not None:
            raise DuplicateCollectionMembershipError(
                f"{kind.value} {member_id.strip()} is already in this collection.",
            )

        timestamp = now or datetime.now(UTC)
        membership = CollectionMembership.create(
            collection_id=collection.id,
            member_kind=kind,
            member_id=member_id,
            reason=reason,
            now=timestamp,
        )

        self._repository.add_membership(membership)
        self._repository.save(collection.touch(timestamp))
        self._repository.add_activity(
            CollectionActivity.create(
                collection_id=collection.id,
                workspace_id=workspace_id,
                activity_type="member_added",
                member_kind=kind,
                member_id=membership.member_id,
                detail=membership.reason,
                now=timestamp,
            )
        )
        self._emit(
            CollectionMemberAdded(
                collection_id=collection.id.value,
                workspace_id=workspace_id,
                member_kind=kind.value,
                member_id=membership.member_id,
                reason=membership.reason,
                occurred_at=timestamp,
            )
        )
        return CollectionMembershipDto.from_membership(membership)

    def remove_member(
        self,
        collection_id: str,
        *,
        workspace_id: WorkspaceId,
        member_kind: str,
        member_id: str,
        now: datetime | None = None,
    ) -> None:
        collection = self._require_collection(collection_id, workspace_id=workspace_id)
        kind = parse_member_kind(member_kind)
        removed = self._repository.remove_membership(
            collection_id=collection.id,
            member_kind=kind,
            member_id=member_id.strip(),
            workspace_id=workspace_id,
        )
        if removed is None:
            raise CollectionMembershipNotFoundError(
                f"{kind.value} {member_id.strip()} is not in this collection.",
            )

        timestamp = now or datetime.now(UTC)
        self._repository.save(collection.touch(timestamp))
        self._repository.add_activity(
            CollectionActivity.create(
                collection_id=collection.id,
                workspace_id=workspace_id,
                activity_type="member_removed",
                member_kind=kind,
                member_id=removed.member_id,
                detail=f"Removed {kind.value}",
                now=timestamp,
            )
        )
        self._emit(
            CollectionMemberRemoved(
                collection_id=collection.id.value,
                workspace_id=workspace_id,
                member_kind=kind.value,
                member_id=removed.member_id,
                occurred_at=timestamp,
            )
        )

    def resolve_search_member_ids(
        self,
        collection_id: str,
        *,
        workspace_id: WorkspaceId,
    ) -> tuple[frozenset[str], frozenset[str]]:
        """Return (document_ids, knowledge_item_ids) for search filtering."""
        collection = self._require_collection(collection_id, workspace_id=workspace_id)
        grouped = self._repository.member_ids_for_kinds(
            collection.id,
            workspace_id=workspace_id,
            kinds=(CollectionMemberKind.DOCUMENT, CollectionMemberKind.KNOWLEDGE),
        )
        return (
            grouped.get(CollectionMemberKind.DOCUMENT, frozenset()),
            grouped.get(CollectionMemberKind.KNOWLEDGE, frozenset()),
        )

    def _require_collection(
        self,
        collection_id: str,
        *,
        workspace_id: WorkspaceId,
    ) -> Collection:
        try:
            parsed_id = CollectionId(collection_id)
        except InvalidCollectionIdError as exc:
            raise CollectionNotFoundError(f"Collection {collection_id} was not found.") from exc
        collection = self._repository.get_by_id(parsed_id, workspace_id=workspace_id)
        if collection is None:
            raise CollectionNotFoundError(f"Collection {collection_id} was not found.")
        return collection

    def _emit(self, event: object) -> None:
        if self._publish is not None:
            self._publish(event)
