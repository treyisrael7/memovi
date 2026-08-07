"""In-memory collection repository for unit tests."""

from __future__ import annotations

from collections.abc import Sequence

from memovi_shared import WorkspaceId

from memovi_memory.domain.entities import Collection, CollectionActivity, CollectionMembership
from memovi_memory.domain.value_objects import CollectionId, CollectionMemberKind


class InMemoryCollectionRepository:
    def __init__(self) -> None:
        self.collections: dict[str, Collection] = {}
        self.memberships: dict[str, CollectionMembership] = {}
        self.activities: list[CollectionActivity] = []

    def add(self, collection: Collection) -> None:
        self.collections[collection.id.value] = collection

    def save(self, collection: Collection) -> None:
        self.collections[collection.id.value] = collection

    def get_by_id(
        self,
        collection_id: CollectionId,
        *,
        workspace_id: WorkspaceId,
    ) -> Collection | None:
        collection = self.collections.get(collection_id.value)
        if collection is None or collection.workspace_id != workspace_id:
            return None
        return collection

    def list_by_workspace(self, *, workspace_id: WorkspaceId) -> Sequence[Collection]:
        items = [
            collection
            for collection in self.collections.values()
            if collection.workspace_id == workspace_id
        ]
        return sorted(items, key=lambda item: (item.metadata.name.lower(), item.created_at))

    def delete(
        self,
        collection_id: CollectionId,
        *,
        workspace_id: WorkspaceId,
    ) -> bool:
        collection = self.get_by_id(collection_id, workspace_id=workspace_id)
        if collection is None:
            return False
        del self.collections[collection_id.value]
        self.memberships = {
            key: membership
            for key, membership in self.memberships.items()
            if membership.collection_id != collection_id
        }
        self.activities = [
            activity
            for activity in self.activities
            if activity.collection_id != collection_id
        ]
        return True

    def add_membership(self, membership: CollectionMembership) -> None:
        key = self._membership_key(
            membership.collection_id,
            membership.member_kind,
            membership.member_id,
        )
        self.memberships[key] = membership

    def get_membership(
        self,
        *,
        collection_id: CollectionId,
        member_kind: CollectionMemberKind,
        member_id: str,
        workspace_id: WorkspaceId,
    ) -> CollectionMembership | None:
        if self.get_by_id(collection_id, workspace_id=workspace_id) is None:
            return None
        return self.memberships.get(
            self._membership_key(collection_id, member_kind, member_id)
        )

    def list_memberships(
        self,
        collection_id: CollectionId,
        *,
        workspace_id: WorkspaceId,
        member_kind: CollectionMemberKind | None = None,
        query: str | None = None,
    ) -> Sequence[CollectionMembership]:
        if self.get_by_id(collection_id, workspace_id=workspace_id) is None:
            return []
        items = [
            membership
            for membership in self.memberships.values()
            if membership.collection_id == collection_id
            and (member_kind is None or membership.member_kind == member_kind)
        ]
        items.sort(key=lambda item: item.added_at, reverse=True)
        if query:
            needle = query.strip().lower()
            if needle:
                items = [
                    item
                    for item in items
                    if needle in item.member_id.lower()
                    or needle in item.reason.lower()
                    or needle in item.member_kind.value
                ]
        return items

    def remove_membership(
        self,
        *,
        collection_id: CollectionId,
        member_kind: CollectionMemberKind,
        member_id: str,
        workspace_id: WorkspaceId,
    ) -> CollectionMembership | None:
        membership = self.get_membership(
            collection_id=collection_id,
            member_kind=member_kind,
            member_id=member_id,
            workspace_id=workspace_id,
        )
        if membership is None:
            return None
        del self.memberships[
            self._membership_key(collection_id, member_kind, member_id)
        ]
        return membership

    def count_memberships_by_kind(
        self,
        collection_id: CollectionId,
        *,
        workspace_id: WorkspaceId,
    ) -> dict[str, int]:
        counts: dict[str, int] = {}
        for membership in self.list_memberships(collection_id, workspace_id=workspace_id):
            counts[membership.member_kind.value] = (
                counts.get(membership.member_kind.value, 0) + 1
            )
        return counts

    def member_ids_for_kinds(
        self,
        collection_id: CollectionId,
        *,
        workspace_id: WorkspaceId,
        kinds: Sequence[CollectionMemberKind],
    ) -> dict[CollectionMemberKind, frozenset[str]]:
        grouped: dict[CollectionMemberKind, set[str]] = {kind: set() for kind in kinds}
        for membership in self.list_memberships(collection_id, workspace_id=workspace_id):
            if membership.member_kind in grouped:
                grouped[membership.member_kind].add(membership.member_id)
        return {kind: frozenset(ids) for kind, ids in grouped.items()}

    def add_activity(self, activity: CollectionActivity) -> None:
        self.activities.append(activity)

    def list_recent_activity(
        self,
        collection_id: CollectionId,
        *,
        workspace_id: WorkspaceId,
        limit: int = 20,
    ) -> Sequence[CollectionActivity]:
        if self.get_by_id(collection_id, workspace_id=workspace_id) is None:
            return []
        items = [
            activity
            for activity in self.activities
            if activity.collection_id == collection_id
            and activity.workspace_id == workspace_id
        ]
        items.sort(key=lambda item: item.occurred_at, reverse=True)
        return items[: max(1, limit)]

    @staticmethod
    def _membership_key(
        collection_id: CollectionId,
        member_kind: CollectionMemberKind,
        member_id: str,
    ) -> str:
        return f"{collection_id.value}:{member_kind.value}:{member_id}"
