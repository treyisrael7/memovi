from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from types import MappingProxyType

from memovi_automation.domain.exceptions import InvalidCapabilityError
from memovi_automation.domain.value_objects.capability_error import CapabilityError
from memovi_automation.domain.value_objects.capability_execution_status import (
    CapabilityExecutionStatus,
)
from memovi_automation.domain.value_objects.permission_mode import PermissionMode


@dataclass(frozen=True, slots=True)
class CapabilityExecutionResult:
    """Normalized outcome of a capability execution pipeline run."""

    execution_id: str
    capability_id: str
    workspace_id: str
    status: CapabilityExecutionStatus
    permission_mode: PermissionMode
    output: object | None = None
    error: CapabilityError | None = None
    duration: float = 0.0
    conversation_id: str | None = None
    correlation_id: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.execution_id.strip():
            raise InvalidCapabilityError("Capability execution result execution_id is required.")
        if not self.capability_id.strip():
            raise InvalidCapabilityError("Capability execution result capability_id is required.")
        if not self.workspace_id.strip():
            raise InvalidCapabilityError("Capability execution result workspace_id is required.")
        if self.duration < 0:
            raise InvalidCapabilityError("Capability execution result duration cannot be negative.")
        if self.status == CapabilityExecutionStatus.COMPLETED and self.error is not None:
            raise InvalidCapabilityError("Completed executions cannot include an error.")
        if self.status == CapabilityExecutionStatus.FAILED and self.error is None:
            raise InvalidCapabilityError("Failed executions must include an error.")
        if not isinstance(self.metadata, Mapping):
            raise InvalidCapabilityError("Capability execution result metadata must be a mapping.")

        object.__setattr__(self, "execution_id", self.execution_id.strip())
        object.__setattr__(self, "capability_id", self.capability_id.strip())
        object.__setattr__(self, "workspace_id", self.workspace_id.strip())
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))
