from typing import Protocol


class EventPublisher(Protocol):
    """Publishes search domain events to downstream consumers."""

    def publish(self, event: object) -> None:
        raise NotImplementedError
