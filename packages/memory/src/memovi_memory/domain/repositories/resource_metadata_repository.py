from typing import Protocol

from memovi_shared import WorkspaceId

from memovi_memory.domain.entities.resource_metadata import ResourceMetadata
from memovi_memory.domain.value_objects import CollectionMemberKind


class ResourceMetadataRepository(Protocol):
    """Persistence for polymorphic resource metadata."""

    def get(
        self,
        *,
        workspace_id: WorkspaceId,
        member_kind: CollectionMemberKind,
        member_id: str,
    ) -> ResourceMetadata | None:
        """Load metadata for a target resource, if present."""

    def upsert(self, metadata: ResourceMetadata) -> None:
        """Insert or replace metadata for a target resource."""
