from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from uuid import uuid4

from memovi_shared import WorkspaceId

from memovi_automation.domain.exceptions import InvalidCapabilityError
from memovi_automation.domain.value_objects.capability_execution_policy import (
    CapabilityExecutionPolicy,
)


@dataclass(frozen=True, slots=True)
class CapabilityExecutionRequest:
    """Engine-level request to run a registered capability.

    Distinct from CapabilityRequest: this carries workspace ownership and
    optional conversation correlation for the execution pipeline.
    """

    capability_id: str
    arguments: Mapping[str, object]
    workspace_id: WorkspaceId
    id: str = ""
    conversation_id: str | None = None
    correlation_id: str | None = None
    policy: CapabilityExecutionPolicy | None = None
    source: str = "api"
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        capability_id = self.capability_id.strip()
        request_id = self.id.strip() if self.id else str(uuid4())
        source = self.source.strip() or "api"

        if not capability_id:
            raise InvalidCapabilityError("Capability execution request capability_id is required.")
        if not isinstance(self.workspace_id, WorkspaceId):
            raise InvalidCapabilityError(
                "Capability execution request workspace_id must be a WorkspaceId.",
            )
        if not isinstance(self.arguments, Mapping):
            raise InvalidCapabilityError(
                "Capability execution request arguments must be a mapping.",
            )
        if not request_id:
            raise InvalidCapabilityError("Capability execution request id is required.")
        if self.conversation_id is not None and not self.conversation_id.strip():
            raise InvalidCapabilityError(
                "conversation_id cannot be blank when provided.",
            )
        if self.correlation_id is not None and not self.correlation_id.strip():
            raise InvalidCapabilityError(
                "correlation_id cannot be blank when provided.",
            )
        if not isinstance(self.metadata, Mapping):
            raise InvalidCapabilityError("Capability execution request metadata must be a mapping.")

        object.__setattr__(self, "capability_id", capability_id)
        object.__setattr__(self, "id", request_id)
        object.__setattr__(self, "source", source)
        object.__setattr__(self, "arguments", MappingProxyType(dict(self.arguments)))
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))
        if self.conversation_id is not None:
            object.__setattr__(self, "conversation_id", self.conversation_id.strip())
        if self.correlation_id is not None:
            object.__setattr__(self, "correlation_id", self.correlation_id.strip())

    @classmethod
    def create(
        cls,
        *,
        capability_id: str,
        workspace_id: WorkspaceId,
        arguments: Mapping[str, object] | None = None,
        request_id: str | None = None,
        conversation_id: str | None = None,
        correlation_id: str | None = None,
        policy: CapabilityExecutionPolicy | None = None,
        source: str = "api",
        metadata: Mapping[str, object] | None = None,
    ) -> CapabilityExecutionRequest:
        return cls(
            capability_id=capability_id,
            workspace_id=workspace_id,
            arguments={} if arguments is None else arguments,
            id=request_id or "",
            conversation_id=conversation_id,
            correlation_id=correlation_id,
            policy=policy,
            source=source,
            metadata={} if metadata is None else metadata,
        )
