from typing import Protocol


class EventPublisher(Protocol):
    """Publishes memory domain events to downstream consumers."""

    def publish(self, event: object) -> None:
        raise NotImplementedError
