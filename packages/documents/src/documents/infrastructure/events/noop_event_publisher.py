class CollectingEventPublisher:
    """In-memory event publisher for tests and local diagnostics."""

    def __init__(self) -> None:
        self.events: list[object] = []

    def publish(self, event: object) -> None:
        self.events.append(event)


class NoOpEventPublisher:
    """Discards published events when no downstream consumer is configured."""

    def publish(self, event: object) -> None:
        return None
