import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from memovi_shared import WorkspaceId

from memovi_memory.domain.exceptions import InvalidChunkError, InvalidDocumentReferenceError
from memovi_memory.domain.value_objects import ChunkId, ChunkIndex, KnowledgeItemId


@dataclass(frozen=True, slots=True)
class Chunk:
    """Deterministic structural unit derived from a normalized document."""

    id: ChunkId
    workspace_id: WorkspaceId
    knowledge_item_id: KnowledgeItemId | None
    document_id: str
    document_version_id: str
    chunk_index: ChunkIndex
    text: str
    created_at: datetime

    def __post_init__(self) -> None:
        if not self.document_id:
            raise InvalidChunkError("Document ID is required.")
        if not self.document_version_id:
            raise InvalidChunkError("Document version ID is required.")
        _validate_document_reference(self.document_id)
        _validate_document_reference(self.document_version_id)
        if not self.text:
            raise InvalidChunkError("Chunk text is required.")

    @classmethod
    def create(
        cls,
        *,
        workspace_id: WorkspaceId,
        document_id: str,
        document_version_id: str,
        chunk_index: ChunkIndex,
        text: str,
        knowledge_item_id: KnowledgeItemId | None = None,
        now: datetime | None = None,
    ) -> Chunk:
        normalized_text = text.strip()
        if not normalized_text:
            raise InvalidChunkError("Chunk text is required.")

        return cls(
            id=ChunkId.new(),
            workspace_id=workspace_id,
            knowledge_item_id=knowledge_item_id,
            document_id=document_id,
            document_version_id=document_version_id,
            chunk_index=chunk_index,
            text=normalized_text,
            created_at=now or datetime.now(UTC),
        )


def _validate_document_reference(value: str) -> None:
    try:
        uuid.UUID(value)
    except ValueError as exc:
        raise InvalidDocumentReferenceError(
            "Document references on chunks must be valid UUIDs.",
        ) from exc
