from typing import Protocol


class EventPublisher(Protocol):
    """Publishes search domain events to downstream consumers."""

    def publish(self, event: object) -> None:
        raise NotImplementedError


class EmbeddingProvider(Protocol):
    """Produces embedding metadata for searchable content without coupling to AI SDKs."""

    def model_id(self) -> str:
        raise NotImplementedError

    def dimensions(self) -> int:
        raise NotImplementedError
