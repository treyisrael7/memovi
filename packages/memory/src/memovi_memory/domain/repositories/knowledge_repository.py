from typing import Protocol

from memovi_memory.domain.entities import KnowledgeItem
from memovi_memory.domain.value_objects import KnowledgeItemId


class KnowledgeRepository(Protocol):
    """Persistence contract for durable knowledge items."""

    def get_by_id(self, knowledge_item_id: KnowledgeItemId) -> KnowledgeItem | None:
        raise NotImplementedError

    def get_by_document_version(
        self,
        *,
        document_id: str,
        document_version_id: str,
    ) -> KnowledgeItem | None:
        raise NotImplementedError

    def add(self, knowledge_item: KnowledgeItem) -> None:
        raise NotImplementedError

    def save(self, knowledge_item: KnowledgeItem) -> None:
        raise NotImplementedError
