from dataclasses import dataclass
from datetime import datetime

from memovi_memory.domain.entities import Chunk


@dataclass(frozen=True, slots=True)
class ChunkDto:
    id: str
    knowledge_item_id: str | None
    document_id: str
    document_version_id: str
    chunk_index: int
    text: str
    created_at: datetime

    @classmethod
    def from_chunk(cls, chunk: Chunk) -> ChunkDto:
        return cls(
            id=chunk.id.value,
            knowledge_item_id=(
                chunk.knowledge_item_id.value if chunk.knowledge_item_id is not None else None
            ),
            document_id=chunk.document_id,
            document_version_id=chunk.document_version_id,
            chunk_index=chunk.chunk_index.value,
            text=chunk.text,
            created_at=chunk.created_at,
        )
