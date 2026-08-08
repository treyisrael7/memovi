from dataclasses import dataclass
from datetime import datetime

from memovi_memory.domain.entities import ResourceMetadata


@dataclass(frozen=True, slots=True)
class ResourceMetadataDto:
    workspace_id: str
    member_kind: str
    member_id: str
    title: str | None
    description: str | None
    notes: str | None
    updated_at: datetime

    @classmethod
    def from_metadata(cls, metadata: ResourceMetadata) -> ResourceMetadataDto:
        return cls(
            workspace_id=metadata.workspace_id.value,
            member_kind=metadata.member_kind.value,
            member_id=metadata.member_id,
            title=metadata.title,
            description=metadata.description,
            notes=metadata.notes,
            updated_at=metadata.updated_at,
        )
