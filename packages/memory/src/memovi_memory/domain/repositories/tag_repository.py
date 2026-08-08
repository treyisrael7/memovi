from collections.abc import Sequence
from typing import Protocol

from memovi_shared import WorkspaceId

from memovi_memory.domain.entities.tag import Tag
from memovi_memory.domain.entities.tag_assignment import TagAssignment
from memovi_memory.domain.value_objects import CollectionMemberKind, TagId


class TagRepository(Protocol):
    """Persistence for tags and tag assignments."""

    def add(self, tag: Tag) -> None:
        """Persist a new tag."""

    def save(self, tag: Tag) -> None:
        """Update an existing tag."""

    def get_by_id(self, tag_id: TagId, *, workspace_id: WorkspaceId) -> Tag | None:
        """Load a tag scoped to a workspace."""

    def get_by_name_key(self, name_key: str, *, workspace_id: WorkspaceId) -> Tag | None:
        """Load a tag by case-insensitive name key within a workspace."""

    def list_by_workspace(self, *, workspace_id: WorkspaceId) -> Sequence[Tag]:
        """List tags in a workspace ordered by name."""

    def suggest_by_prefix(
        self,
        *,
        workspace_id: WorkspaceId,
        prefix: str,
        limit: int = 20,
    ) -> Sequence[Tag]:
        """Suggest tags whose names start with the given prefix (case-insensitive)."""

    def delete(self, tag_id: TagId, *, workspace_id: WorkspaceId) -> bool:
        """Delete a tag and its assignments. Returns True if deleted."""

    def add_assignment(self, assignment: TagAssignment) -> None:
        """Persist a new tag assignment."""

    def get_assignment(
        self,
        *,
        tag_id: TagId,
        member_kind: CollectionMemberKind,
        member_id: str,
        workspace_id: WorkspaceId,
    ) -> TagAssignment | None:
        """Load an assignment if it exists in the workspace-scoped tag."""

    def list_assignments(
        self,
        tag_id: TagId,
        *,
        workspace_id: WorkspaceId,
        member_kind: CollectionMemberKind | None = None,
        query: str | None = None,
    ) -> Sequence[TagAssignment]:
        """List assignments, optionally filtered by kind and free-text query."""

    def list_tags_for_member(
        self,
        *,
        workspace_id: WorkspaceId,
        member_kind: CollectionMemberKind,
        member_id: str,
    ) -> Sequence[Tag]:
        """List tags assigned to a specific target resource."""

    def remove_assignment(
        self,
        *,
        tag_id: TagId,
        member_kind: CollectionMemberKind,
        member_id: str,
        workspace_id: WorkspaceId,
    ) -> TagAssignment | None:
        """Remove and return an assignment, or None if missing."""

    def count_assignments_by_kind(
        self,
        tag_id: TagId,
        *,
        workspace_id: WorkspaceId,
    ) -> dict[str, int]:
        """Return assignment counts keyed by member kind."""

    def member_ids_for_kinds(
        self,
        tag_id: TagId,
        *,
        workspace_id: WorkspaceId,
        kinds: Sequence[CollectionMemberKind],
    ) -> dict[CollectionMemberKind, frozenset[str]]:
        """Return member IDs grouped by kind for search filtering."""
