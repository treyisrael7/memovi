from dataclasses import dataclass

from memovi_automation.domain.exceptions import InvalidCapabilityError
from memovi_automation.domain.value_objects.permission_mode import PermissionMode


@dataclass(frozen=True, slots=True)
class CapabilityExecutionPolicy:
    """Immutable execution constraints for a single capability invocation.

    Policies govern timeouts, cancellation, and permission decision mode.
    Retries and orchestration are intentionally out of scope.
    """

    timeout_seconds: float | None = 30.0
    cancellable: bool = True
    permission_mode: PermissionMode | None = None

    def __post_init__(self) -> None:
        if self.timeout_seconds is not None and self.timeout_seconds <= 0:
            raise InvalidCapabilityError(
                "Capability execution timeout_seconds must be positive when provided.",
            )
        if self.permission_mode is not None and not isinstance(
            self.permission_mode,
            PermissionMode,
        ):
            raise InvalidCapabilityError(
                "Capability execution permission_mode must be a PermissionMode.",
            )


DEFAULT_EXECUTION_POLICY = CapabilityExecutionPolicy()
