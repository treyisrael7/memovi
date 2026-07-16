import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from memovi_memory.domain.entities import Chunk, KnowledgeItem
from memovi_memory.domain.exceptions import InvalidKnowledgeMaterializationError
from memovi_memory.domain.services.chunk_generator import ChunkDraft
from memovi_memory.domain.value_objects import ChunkId, KnowledgeItemId

_MATERIALIZATION_NAMESPACE = uuid.UUID("6f3f2f58-7b9a-4d2e-9c11-8a5f0e2d4b61")


@dataclass(frozen=True, slots=True)
class KnowledgeMaterializationResult:
    """Domain entities materialized from chunk drafts."""

    knowledge_item: KnowledgeItem
    chunks: list[Chunk]


class KnowledgeMaterializer:
    """Materializes canonical memory entities from generated chunk drafts."""

    def materialize(
        self,
        *,
        document_id: str,
        document_version_id: str,
        source_type: str,
        mime_type: str,
        chunk_drafts: list[ChunkDraft],
        now: datetime | None = None,
    ) -> KnowledgeMaterializationResult:
        if not chunk_drafts:
            raise InvalidKnowledgeMaterializationError(
                "At least one chunk draft is required to materialize knowledge.",
            )

        timestamp = now or datetime.now(UTC)
        knowledge_item = KnowledgeItem(
            id=_knowledge_item_id(document_id, document_version_id),
            document_id=document_id,
            document_version_id=document_version_id,
            source_type=source_type,
            mime_type=mime_type,
            created_at=timestamp,
            updated_at=timestamp,
        )
        chunks = [
            Chunk(
                id=_chunk_id(document_id, document_version_id, draft.chunk_index.value),
                knowledge_item_id=knowledge_item.id,
                document_id=document_id,
                document_version_id=document_version_id,
                chunk_index=draft.chunk_index,
                text=draft.text,
                created_at=timestamp,
            )
            for draft in chunk_drafts
        ]

        return KnowledgeMaterializationResult(
            knowledge_item=knowledge_item,
            chunks=chunks,
        )


def _knowledge_item_id(document_id: str, document_version_id: str) -> KnowledgeItemId:
    derived_id = uuid.uuid5(
        _MATERIALIZATION_NAMESPACE,
        f"knowledge-item:{document_id}:{document_version_id}",
    )
    return KnowledgeItemId(str(derived_id))


def _chunk_id(document_id: str, document_version_id: str, chunk_index: int) -> ChunkId:
    derived_id = uuid.uuid5(
        _MATERIALIZATION_NAMESPACE,
        f"chunk:{document_id}:{document_version_id}:{chunk_index}",
    )
    return ChunkId(str(derived_id))
