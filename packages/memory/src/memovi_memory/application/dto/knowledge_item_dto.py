from dataclasses import dataclass
from datetime import datetime

from memovi_memory.domain.entities import KnowledgeItem


@dataclass(frozen=True, slots=True)
class KnowledgeItemDto:
    id: str
    document_id: str
    document_version_id: str
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_knowledge_item(cls, knowledge_item: KnowledgeItem) -> KnowledgeItemDto:
        return cls(
            id=knowledge_item.id.value,
            document_id=knowledge_item.document_id,
            document_version_id=knowledge_item.document_version_id,
            created_at=knowledge_item.created_at,
            updated_at=knowledge_item.updated_at,
        )
