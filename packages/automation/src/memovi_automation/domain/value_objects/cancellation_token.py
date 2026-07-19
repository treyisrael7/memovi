from threading import Event

from memovi_automation.domain.exceptions import CapabilityCancelledError


class CancellationToken:
    """Thread-safe cancellation signal for capability execution.

    Not frozen: cancellation is a mutable runtime signal owned by the invoker.
    """

    __slots__ = ("_event",)

    def __init__(self) -> None:
        self._event = Event()

    def cancel(self) -> None:
        self._event.set()

    @property
    def is_cancelled(self) -> bool:
        return self._event.is_set()

    def raise_if_cancelled(self) -> None:
        if self.is_cancelled:
            raise CapabilityCancelledError("Capability invocation was cancelled.")
