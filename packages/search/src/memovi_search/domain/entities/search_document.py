import uuid
from dataclasses import dataclass, replace
from datetime import UTC, datetime

from memovi_search.domain.exceptions import (
    InvalidChunkReferenceError,
    InvalidDocumentReferenceError,
    InvalidSearchDocumentError,
)
from memovi_search.domain.value_objects import SearchDocumentId


@dataclass(frozen=True, slots=True)
class SearchDocument:
    """Searchable representation of a memory chunk from a processed document."""

    id: SearchDocumentId
    document_id: str
    document_version_id: str
    chunk_id: str
    created_at: datetime
    updated_at: datetime

    def __post_init__(self) -> None:
        if not self.document_id:
            raise InvalidSearchDocumentError("Document ID is required.")
        if not self.document_version_id:
            raise InvalidSearchDocumentError("Document version ID is required.")
        if not self.chunk_id:
            raise InvalidSearchDocumentError("Chunk ID is required.")
        _validate_document_reference(self.document_id)
        _validate_document_reference(self.document_version_id)
        _validate_chunk_reference(self.chunk_id)
        if self.updated_at < self.created_at:
            raise InvalidSearchDocumentError(
                "Updated timestamp cannot precede created timestamp.",
            )

    @classmethod
    def register(
        cls,
        *,
        document_id: str,
        document_version_id: str,
        chunk_id: str,
        now: datetime | None = None,
    ) -> SearchDocument:
        timestamp = now or datetime.now(UTC)
        return cls(
            id=SearchDocumentId.new(),
            document_id=document_id,
            document_version_id=document_version_id,
            chunk_id=chunk_id,
            created_at=timestamp,
            updated_at=timestamp,
        )

    def touch(self, now: datetime | None = None) -> SearchDocument:
        """Return a copy with a refreshed ``updated_at`` timestamp."""
        return replace(self, updated_at=now or datetime.now(UTC))


def _validate_document_reference(value: str) -> None:
    try:
        uuid.UUID(value)
    except ValueError as exc:
        raise InvalidDocumentReferenceError(
            "Document references on search documents must be valid UUIDs.",
        ) from exc


def _validate_chunk_reference(value: str) -> None:
    try:
        uuid.UUID(value)
    except ValueError as exc:
        raise InvalidChunkReferenceError(
            "Chunk references on search documents must be valid UUIDs.",
        ) from exc
