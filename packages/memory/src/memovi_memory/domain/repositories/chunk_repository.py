from typing import Protocol

from memovi_memory.domain.entities import Chunk
from memovi_memory.domain.value_objects import ChunkId, KnowledgeItemId


class ChunkRepository(Protocol):
    """Persistence contract for knowledge chunks."""

    def get_by_id(self, chunk_id: ChunkId) -> Chunk | None:
        raise NotImplementedError

    def list_by_knowledge_item_id(self, knowledge_item_id: KnowledgeItemId) -> list[Chunk]:
        raise NotImplementedError

    def add(self, chunk: Chunk) -> None:
        raise NotImplementedError

    def add_many(self, chunks: list[Chunk]) -> None:
        raise NotImplementedError

    def delete_by_knowledge_item_id(self, knowledge_item_id: KnowledgeItemId) -> None:
        raise NotImplementedError
