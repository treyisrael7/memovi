from collections.abc import Sequence
from typing import Protocol

from memovi_shared import WorkspaceId

from memovi_memory.domain.entities.collection import Collection
from memovi_memory.domain.entities.collection_activity import CollectionActivity
from memovi_memory.domain.entities.collection_membership import CollectionMembership
from memovi_memory.domain.value_objects import CollectionId, CollectionMemberKind


class CollectionRepository(Protocol):
    """Persistence for collections, memberships, and activity."""

    def add(self, collection: Collection) -> None:
        """Persist a new collection."""

    def save(self, collection: Collection) -> None:
        """Update an existing collection."""

    def get_by_id(
        self,
        collection_id: CollectionId,
        *,
        workspace_id: WorkspaceId,
    ) -> Collection | None:
        """Load a collection scoped to a workspace."""

    def list_by_workspace(self, *, workspace_id: WorkspaceId) -> Sequence[Collection]:
        """List collections in a workspace ordered by name."""

    def delete(
        self,
        collection_id: CollectionId,
        *,
        workspace_id: WorkspaceId,
    ) -> bool:
        """Delete a collection and its memberships/activity. Returns True if deleted."""

    def add_membership(self, membership: CollectionMembership) -> None:
        """Persist a new membership."""

    def get_membership(
        self,
        *,
        collection_id: CollectionId,
        member_kind: CollectionMemberKind,
        member_id: str,
        workspace_id: WorkspaceId,
    ) -> CollectionMembership | None:
        """Load a membership if it exists in the workspace-scoped collection."""

    def list_memberships(
        self,
        collection_id: CollectionId,
        *,
        workspace_id: WorkspaceId,
        member_kind: CollectionMemberKind | None = None,
        query: str | None = None,
    ) -> Sequence[CollectionMembership]:
        """List memberships, optionally filtered by kind and free-text query."""

    def remove_membership(
        self,
        *,
        collection_id: CollectionId,
        member_kind: CollectionMemberKind,
        member_id: str,
        workspace_id: WorkspaceId,
    ) -> CollectionMembership | None:
        """Remove and return a membership, or None if missing."""

    def count_memberships_by_kind(
        self,
        collection_id: CollectionId,
        *,
        workspace_id: WorkspaceId,
    ) -> dict[str, int]:
        """Return membership counts keyed by member kind."""

    def member_ids_for_kinds(
        self,
        collection_id: CollectionId,
        *,
        workspace_id: WorkspaceId,
        kinds: Sequence[CollectionMemberKind],
    ) -> dict[CollectionMemberKind, frozenset[str]]:
        """Return member IDs grouped by kind for search filtering."""

    def add_activity(self, activity: CollectionActivity) -> None:
        """Append an activity entry."""

    def list_recent_activity(
        self,
        collection_id: CollectionId,
        *,
        workspace_id: WorkspaceId,
        limit: int = 20,
    ) -> Sequence[CollectionActivity]:
        """List recent activity newest-first."""
