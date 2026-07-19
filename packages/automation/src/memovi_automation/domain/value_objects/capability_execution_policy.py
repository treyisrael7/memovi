from dataclasses import dataclass

from memovi_automation.domain.exceptions import InvalidCapabilityError


@dataclass(frozen=True, slots=True)
class CapabilityExecutionPolicy:
    """Immutable execution constraints for a single capability invocation.

    Policies govern timeouts and cancellation. Retries and orchestration are
    intentionally out of scope.
    """

    timeout_seconds: float | None = 30.0
    cancellable: bool = True

    def __post_init__(self) -> None:
        if self.timeout_seconds is not None and self.timeout_seconds <= 0:
            raise InvalidCapabilityError(
                "Capability execution timeout_seconds must be positive when provided.",
            )


DEFAULT_EXECUTION_POLICY = CapabilityExecutionPolicy()
