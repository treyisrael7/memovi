import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from memovi_memory.domain.exceptions import InvalidDocumentReferenceError, InvalidKnowledgeItemError
from memovi_memory.domain.value_objects import KnowledgeItemId


@dataclass(frozen=True, slots=True)
class KnowledgeItem:
    """Durable knowledge derived from a processed document version."""

    id: KnowledgeItemId
    document_id: str
    document_version_id: str
    created_at: datetime
    updated_at: datetime

    def __post_init__(self) -> None:
        if not self.document_id:
            raise InvalidKnowledgeItemError("Document ID is required.")
        if not self.document_version_id:
            raise InvalidKnowledgeItemError("Document version ID is required.")
        _validate_document_reference(self.document_id)
        _validate_document_reference(self.document_version_id)

    @classmethod
    def create(
        cls,
        *,
        document_id: str,
        document_version_id: str,
        now: datetime | None = None,
    ) -> KnowledgeItem:
        timestamp = now or datetime.now(UTC)
        return cls(
            id=KnowledgeItemId.new(),
            document_id=document_id,
            document_version_id=document_version_id,
            created_at=timestamp,
            updated_at=timestamp,
        )


def _validate_document_reference(value: str) -> None:
    try:
        uuid.UUID(value)
    except ValueError as exc:
        raise InvalidDocumentReferenceError(
            "Document references on knowledge items must be valid UUIDs.",
        ) from exc
