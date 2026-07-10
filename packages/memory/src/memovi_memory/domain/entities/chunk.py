from dataclasses import dataclass
from datetime import UTC, datetime

from memovi_memory.domain.exceptions import InvalidChunkError
from memovi_memory.domain.value_objects import ChunkId, ChunkIndex, KnowledgeItemId


@dataclass(frozen=True, slots=True)
class Chunk:
    """A bounded passage of knowledge materialized from a parent knowledge item."""

    id: ChunkId
    knowledge_item_id: KnowledgeItemId
    index: ChunkIndex
    content: str
    created_at: datetime

    def __post_init__(self) -> None:
        if not self.content:
            raise InvalidChunkError("Chunk content is required.")

    @classmethod
    def create(
        cls,
        *,
        knowledge_item_id: KnowledgeItemId,
        index: ChunkIndex,
        content: str,
        now: datetime | None = None,
    ) -> Chunk:
        return cls(
            id=ChunkId.new(),
            knowledge_item_id=knowledge_item_id,
            index=index,
            content=content,
            created_at=now or datetime.now(UTC),
        )
