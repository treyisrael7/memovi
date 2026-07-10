from dataclasses import dataclass
from datetime import datetime

from memovi_memory.domain.value_objects import KnowledgeItemId


@dataclass(frozen=True, slots=True)
class ChunksGenerated:
    """Domain fact emitted after retrievable chunks are created for a knowledge item."""

    knowledge_item_id: KnowledgeItemId
    chunk_count: int
    occurred_at: datetime
