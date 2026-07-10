from collections import defaultdict
from collections.abc import Callable


class InProcessEventDispatcher:
    """Synchronously dispatches domain events to registered subscribers."""

    def __init__(self) -> None:
        self._subscribers: dict[type[object], list[Callable[[object], None]]] = defaultdict(list)
        self.published_events: list[object] = []

    def subscribe(
        self,
        event_type: type[object],
        handler: Callable[[object], None],
    ) -> None:
        self._subscribers[event_type].append(handler)

    def publish(self, event: object) -> None:
        self.published_events.append(event)
        for handler in self._subscribers.get(type(event), []):
            handler(event)


class TransactionScopedEventPublisher:
    """Buffers published events until the surrounding transaction commits."""

    def __init__(self, inner: InProcessEventDispatcher) -> None:
        self._inner = inner
        self._pending: list[object] = []

    def publish(self, event: object) -> None:
        self._pending.append(event)

    def flush(self) -> None:
        for event in self._pending:
            self._inner.publish(event)
        self._pending.clear()
