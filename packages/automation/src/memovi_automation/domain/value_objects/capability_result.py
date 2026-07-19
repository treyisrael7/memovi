from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType

from memovi_automation.domain.exceptions import InvalidCapabilityError
from memovi_automation.domain.value_objects.capability_error import CapabilityError


@dataclass(frozen=True, slots=True)
class CapabilityResult:
    """Immutable outcome of a single capability invocation."""

    request_id: str
    capability_id: str
    success: bool
    output: object | None = None
    error: CapabilityError | None = None
    cancelled: bool = False
    timed_out: bool = False
    duration: float = 0.0
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        request_id = self.request_id.strip()
        capability_id = self.capability_id.strip()

        if not request_id:
            raise InvalidCapabilityError("Capability result request_id is required.")
        if not capability_id:
            raise InvalidCapabilityError("Capability result capability_id is required.")
        if self.duration < 0:
            raise InvalidCapabilityError("Capability result duration cannot be negative.")
        if self.success and self.error is not None:
            raise InvalidCapabilityError("Successful capability results cannot include an error.")
        if self.success and (self.cancelled or self.timed_out):
            raise InvalidCapabilityError(
                "Successful capability results cannot be cancelled or timed out.",
            )
        if not self.success and self.error is None:
            raise InvalidCapabilityError("Failed capability results must include an error.")
        if self.cancelled and self.timed_out:
            raise InvalidCapabilityError(
                "Capability results cannot be both cancelled and timed out.",
            )
        if self.error is not None and not isinstance(self.error, CapabilityError):
            raise InvalidCapabilityError("Capability result error must be a CapabilityError.")
        if not isinstance(self.metadata, Mapping):
            raise InvalidCapabilityError("Capability result metadata must be a mapping.")

        object.__setattr__(self, "request_id", request_id)
        object.__setattr__(self, "capability_id", capability_id)
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))

    @classmethod
    def success_result(
        cls,
        *,
        request_id: str,
        capability_id: str,
        output: object | None = None,
        duration: float = 0.0,
        metadata: Mapping[str, object] | None = None,
    ) -> CapabilityResult:
        return cls(
            request_id=request_id,
            capability_id=capability_id,
            success=True,
            output=output,
            error=None,
            cancelled=False,
            timed_out=False,
            duration=duration,
            metadata={} if metadata is None else metadata,
        )

    @classmethod
    def failure_result(
        cls,
        *,
        request_id: str,
        capability_id: str,
        error: CapabilityError,
        duration: float = 0.0,
        metadata: Mapping[str, object] | None = None,
        cancelled: bool = False,
        timed_out: bool = False,
    ) -> CapabilityResult:
        return cls(
            request_id=request_id,
            capability_id=capability_id,
            success=False,
            output=None,
            error=error,
            cancelled=cancelled,
            timed_out=timed_out,
            duration=duration,
            metadata={} if metadata is None else metadata,
        )
