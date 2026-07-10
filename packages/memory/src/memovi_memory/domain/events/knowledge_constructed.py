from dataclasses import dataclass
from datetime import datetime

from memovi_memory.domain.value_objects import KnowledgeItemId


@dataclass(frozen=True, slots=True)
class KnowledgeConstructed:
    """Domain fact emitted after a knowledge item is materialized from a document."""

    knowledge_item_id: KnowledgeItemId
    document_id: str
    document_version_id: str
    occurred_at: datetime
