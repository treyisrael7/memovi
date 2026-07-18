import uuid
from dataclasses import dataclass, replace
from datetime import UTC, datetime

from memovi_shared import WorkspaceId

from memovi_search.domain.exceptions import (
    InvalidDocumentReferenceError,
    InvalidKnowledgeItemReferenceError,
    InvalidSearchDocumentError,
)
from memovi_search.domain.value_objects import SearchDocumentId


@dataclass(frozen=True, slots=True)
class SearchDocument:
    """Searchable projection of durable knowledge derived from a processed document."""

    id: SearchDocumentId
    workspace_id: WorkspaceId
    knowledge_item_id: str
    document_id: str
    document_version_id: str
    source_type: str
    mime_type: str
    searchable_text: str
    created_at: datetime
    updated_at: datetime

    def __post_init__(self) -> None:
        if not self.knowledge_item_id:
            raise InvalidSearchDocumentError("Knowledge item ID is required.")
        if not self.document_id:
            raise InvalidSearchDocumentError("Document ID is required.")
        if not self.document_version_id:
            raise InvalidSearchDocumentError("Document version ID is required.")
        if not self.source_type.strip():
            raise InvalidSearchDocumentError("Source type is required.")
        if not self.mime_type.strip():
            raise InvalidSearchDocumentError("MIME type is required.")
        if not self.searchable_text:
            raise InvalidSearchDocumentError("Searchable text is required.")
        _validate_knowledge_item_reference(self.knowledge_item_id)
        _validate_document_reference(self.document_id)
        _validate_document_reference(self.document_version_id)
        if self.updated_at < self.created_at:
            raise InvalidSearchDocumentError(
                "Updated timestamp cannot precede created timestamp.",
            )

    @classmethod
    def create(
        cls,
        *,
        workspace_id: WorkspaceId,
        knowledge_item_id: str,
        document_id: str,
        document_version_id: str,
        source_type: str,
        mime_type: str,
        searchable_text: str,
        now: datetime | None = None,
    ) -> SearchDocument:
        normalized_text = searchable_text.strip()
        if not normalized_text:
            raise InvalidSearchDocumentError("Searchable text is required.")
        normalized_source_type = source_type.strip()
        if not normalized_source_type:
            raise InvalidSearchDocumentError("Source type is required.")
        normalized_mime_type = mime_type.strip()
        if not normalized_mime_type:
            raise InvalidSearchDocumentError("MIME type is required.")

        timestamp = now or datetime.now(UTC)
        return cls(
            id=SearchDocumentId.new(),
            workspace_id=workspace_id,
            knowledge_item_id=knowledge_item_id,
            document_id=document_id,
            document_version_id=document_version_id,
            source_type=normalized_source_type,
            mime_type=normalized_mime_type,
            searchable_text=normalized_text,
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


def _validate_knowledge_item_reference(value: str) -> None:
    try:
        uuid.UUID(value)
    except ValueError as exc:
        raise InvalidKnowledgeItemReferenceError(
            "Knowledge item references on search documents must be valid UUIDs.",
        ) from exc
