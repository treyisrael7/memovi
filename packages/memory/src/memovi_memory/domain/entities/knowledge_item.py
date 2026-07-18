import uuid
from dataclasses import dataclass, replace
from datetime import UTC, datetime

from memovi_shared import WorkspaceId

from memovi_memory.domain.exceptions import InvalidDocumentReferenceError, InvalidKnowledgeItemError
from memovi_memory.domain.value_objects import KnowledgeItemId


@dataclass(frozen=True, slots=True)
class KnowledgeItem:
    """Durable knowledge derived from a processed document version."""

    id: KnowledgeItemId
    workspace_id: WorkspaceId
    document_id: str
    document_version_id: str
    source_type: str
    mime_type: str
    created_at: datetime
    updated_at: datetime

    def __post_init__(self) -> None:
        if not self.document_id:
            raise InvalidKnowledgeItemError("Document ID is required.")
        if not self.document_version_id:
            raise InvalidKnowledgeItemError("Document version ID is required.")
        if not self.source_type.strip():
            raise InvalidKnowledgeItemError("Source type is required.")
        if not self.mime_type.strip():
            raise InvalidKnowledgeItemError("MIME type is required.")
        _validate_document_reference(self.document_id)
        _validate_document_reference(self.document_version_id)
        if self.updated_at < self.created_at:
            raise InvalidKnowledgeItemError("Updated timestamp cannot precede created timestamp.")

    @classmethod
    def create(
        cls,
        *,
        workspace_id: WorkspaceId,
        document_id: str,
        document_version_id: str,
        source_type: str,
        mime_type: str,
        now: datetime | None = None,
    ) -> KnowledgeItem:
        normalized_source_type = source_type.strip()
        if not normalized_source_type:
            raise InvalidKnowledgeItemError("Source type is required.")
        normalized_mime_type = mime_type.strip()
        if not normalized_mime_type:
            raise InvalidKnowledgeItemError("MIME type is required.")

        timestamp = now or datetime.now(UTC)
        return cls(
            id=KnowledgeItemId.new(),
            workspace_id=workspace_id,
            document_id=document_id,
            document_version_id=document_version_id,
            source_type=normalized_source_type,
            mime_type=normalized_mime_type,
            created_at=timestamp,
            updated_at=timestamp,
        )

    def touch(self, now: datetime | None = None) -> KnowledgeItem:
        """Return a copy with a refreshed ``updated_at`` timestamp."""
        return replace(self, updated_at=now or datetime.now(UTC))


def _validate_document_reference(value: str) -> None:
    try:
        uuid.UUID(value)
    except ValueError as exc:
        raise InvalidDocumentReferenceError(
            "Document references on knowledge items must be valid UUIDs.",
        ) from exc
