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
    connector_id: str | None = None
    external_id: str | None = None
    external_path: str | None = None

    @classmethod
    def create(
        cls,
        *,
        workspace_id: WorkspaceId,
        name: DocumentName,
        mime_type: MimeType,
        source_type: SourceType,
        now: datetime | None = None,
        connector_id: str | None = None,
        external_id: str | None = None,
        external_path: str | None = None,
    ) -> Document:
        return cls(
            id=DocumentId.new(),
            workspace_id=workspace_id,
            name=name,
            mime_type=mime_type,
            source_type=source_type,
            created_at=now or datetime.now(UTC),
            connector_id=connector_id,
            external_id=external_id,
            external_path=external_path,
        )

    def with_identity(
        self,
        *,
        name: DocumentName | None = None,
        mime_type: MimeType | None = None,
        external_path: str | None = None,
    ) -> Document:
        """Return a copy with updated display identity fields."""
        return Document(
            id=self.id,
            workspace_id=self.workspace_id,
            name=name or self.name,
            mime_type=mime_type or self.mime_type,
            source_type=self.source_type,
            created_at=self.created_at,
            connector_id=self.connector_id,
            external_id=self.external_id,
            external_path=self.external_path if external_path is None else external_path,
        )
