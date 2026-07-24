from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType

from memovi_shared import WorkspaceId

from memovi_automation.domain.exceptions import InvalidCapabilityError
from memovi_automation.domain.value_objects.cancellation_token import CancellationToken


@dataclass(frozen=True, slots=True)
class CapabilityExecutionContext:
    """Runtime context for the Capability Execution Engine.

    Carries ownership, cancellation, and optional conversation linkage.
    Granted permissions are applied by the engine after policy approval.
    """

    workspace_id: WorkspaceId
    cancellation: CancellationToken
    conversation_id: str | None = None
    correlation_id: str | None = None
    source: str = "api"
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.workspace_id, WorkspaceId):
            raise InvalidCapabilityError(
                "Capability execution context workspace_id must be a WorkspaceId.",
            )
        if not isinstance(self.cancellation, CancellationToken):
            raise InvalidCapabilityError(
                "Capability execution context cancellation must be a CancellationToken.",
            )
        source = self.source.strip() or "api"
        object.__setattr__(self, "source", source)
        if self.conversation_id is not None:
            conversation_id = self.conversation_id.strip()
            if not conversation_id:
                raise InvalidCapabilityError(
                    "conversation_id cannot be blank when provided.",
                )
            object.__setattr__(self, "conversation_id", conversation_id)
        if self.correlation_id is not None:
            correlation_id = self.correlation_id.strip()
            if not correlation_id:
                raise InvalidCapabilityError(
                    "correlation_id cannot be blank when provided.",
                )
            object.__setattr__(self, "correlation_id", correlation_id)
        if not isinstance(self.metadata, Mapping):
            raise InvalidCapabilityError(
                "Capability execution context metadata must be a mapping.",
            )
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))

    def is_cancelled(self) -> bool:
        return self.cancellation.is_cancelled

    @classmethod
    def create(
        cls,
        *,
        workspace_id: WorkspaceId,
        cancellation: CancellationToken | None = None,
        conversation_id: str | None = None,
        correlation_id: str | None = None,
        source: str = "api",
        metadata: Mapping[str, object] | None = None,
    ) -> CapabilityExecutionContext:
        return cls(
            workspace_id=workspace_id,
            cancellation=CancellationToken() if cancellation is None else cancellation,
            conversation_id=conversation_id,
            correlation_id=correlation_id,
            source=source,
            metadata={} if metadata is None else metadata,
        )
