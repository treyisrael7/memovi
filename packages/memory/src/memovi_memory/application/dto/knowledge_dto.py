from dataclasses import dataclass
from datetime import datetime

from memovi_memory.application.dto.chunk_dto import ChunkDto
from memovi_memory.application.dto.knowledge_item_dto import KnowledgeItemDto
from memovi_memory.domain.entities import Chunk, KnowledgeItem


@dataclass(frozen=True, slots=True)
class KnowledgeDto:
    """Canonical read representation of durable knowledge and its chunks."""

    id: str
    document_id: str
    document_version_id: str
    created_at: datetime
    updated_at: datetime
    chunks: tuple[ChunkDto, ...]

    @classmethod
    def from_knowledge_item_and_chunks(
        cls,
        knowledge_item: KnowledgeItem,
        chunks: list[Chunk],
    ) -> KnowledgeDto:
        item = KnowledgeItemDto.from_knowledge_item(knowledge_item)
        ordered_chunks = sorted(chunks, key=lambda chunk: chunk.chunk_index.value)
        return cls(
            id=item.id,
            document_id=item.document_id,
            document_version_id=item.document_version_id,
            created_at=item.created_at,
            updated_at=item.updated_at,
            chunks=tuple(ChunkDto.from_chunk(chunk) for chunk in ordered_chunks),
        )
