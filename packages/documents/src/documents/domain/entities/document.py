from dataclasses import dataclass
from datetime import UTC, datetime

from memovi_shared import WorkspaceId

from documents.domain.value_objects import DocumentId, DocumentName, MimeType, SourceType


@dataclass(frozen=True, slots=True)
class Document:
    """Normalized representation of imported knowledge content."""

    id: DocumentId
    workspace_id: WorkspaceId
    name: DocumentName
    mime_type: MimeType
    source_type: SourceType
    created_at: datetime

    @classmethod
    def create(
        cls,
        *,
        workspace_id: WorkspaceId,
        name: DocumentName,
        mime_type: MimeType,
        source_type: SourceType,
        now: datetime | None = None,
    ) -> Document:
        return cls(
            id=DocumentId.new(),
            workspace_id=workspace_id,
            name=name,
            mime_type=mime_type,
            source_type=source_type,
            created_at=now or datetime.now(UTC),
        )
