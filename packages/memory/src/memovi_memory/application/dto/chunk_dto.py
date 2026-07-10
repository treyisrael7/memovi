from dataclasses import dataclass
from datetime import datetime

from memovi_memory.domain.entities import Chunk


@dataclass(frozen=True, slots=True)
class ChunkDto:
    id: str
    knowledge_item_id: str
    index: int
    content: str
    created_at: datetime

    @classmethod
    def from_chunk(cls, chunk: Chunk) -> ChunkDto:
        return cls(
            id=chunk.id.value,
            knowledge_item_id=chunk.knowledge_item_id.value,
            index=chunk.index.value,
            content=chunk.content,
            created_at=chunk.created_at,
        )
