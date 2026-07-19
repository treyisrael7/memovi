from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from uuid import uuid4

from memovi_automation.domain.exceptions import InvalidCapabilityError
from memovi_automation.domain.value_objects.capability_execution_policy import (
    CapabilityExecutionPolicy,
)


@dataclass(frozen=True, slots=True)
class CapabilityRequest:
    """Immutable request to invoke a named capability with arguments."""

    capability_id: str
    arguments: Mapping[str, object]
    id: str = ""
    policy: CapabilityExecutionPolicy | None = None

    def __post_init__(self) -> None:
        capability_id = self.capability_id.strip()
        request_id = self.id.strip() if self.id else str(uuid4())

        if not capability_id:
            raise InvalidCapabilityError("Capability request capability_id is required.")
        if not isinstance(self.arguments, Mapping):
            raise InvalidCapabilityError("Capability request arguments must be a mapping.")
        if not request_id:
            raise InvalidCapabilityError("Capability request id is required.")
        if self.policy is not None and not isinstance(self.policy, CapabilityExecutionPolicy):
            raise InvalidCapabilityError(
                "Capability request policy must be a CapabilityExecutionPolicy.",
            )

        object.__setattr__(self, "capability_id", capability_id)
        object.__setattr__(self, "id", request_id)
        object.__setattr__(self, "arguments", MappingProxyType(dict(self.arguments)))

    @classmethod
    def create(
        cls,
        *,
        capability_id: str,
        arguments: Mapping[str, object] | None = None,
        request_id: str | None = None,
        policy: CapabilityExecutionPolicy | None = None,
    ) -> CapabilityRequest:
        return cls(
            capability_id=capability_id,
            arguments={} if arguments is None else arguments,
            id=request_id or "",
            policy=policy,
        )
