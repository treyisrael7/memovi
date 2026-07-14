from typing import Protocol

from memovi_search.application.dto.knowledge_read_dto import KnowledgeReadDto


class EventPublisher(Protocol):
    """Publishes search domain events to downstream consumers."""

    def publish(self, event: object) -> None:
        raise NotImplementedError


class KnowledgeReader(Protocol):
    """Loads canonical knowledge without coupling to the Memory domain."""

    def get_knowledge(self, knowledge_item_id: str) -> KnowledgeReadDto | None:
        raise NotImplementedError
