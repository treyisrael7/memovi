from dataclasses import dataclass
from datetime import UTC, datetime

from documents.domain.value_objects import DocumentId, DocumentName, MimeType, SourceType


@dataclass(frozen=True, slots=True)
class Document:
    """Normalized representation of imported knowledge content."""

    id: DocumentId
    name: DocumentName
    mime_type: MimeType
    source_type: SourceType
    created_at: datetime

    @classmethod
    def create(
        cls,
        *,
        name: DocumentName,
        mime_type: MimeType,
        source_type: SourceType,
        now: datetime | None = None,
    ) -> Document:
        return cls(
            id=DocumentId.new(),
            name=name,
            mime_type=mime_type,
            source_type=source_type,
            created_at=now or datetime.now(UTC),
        )
