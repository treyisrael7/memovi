from collections.abc import Mapping
from dataclasses import dataclass

from memovi_shared import WorkspaceId

from memovi_intelligence.application.ports_capability_execution import (
    CapabilityExecutionPort,
    CapabilityExecutionView,
)
from memovi_intelligence.domain.exceptions import IntelligenceDomainError
from memovi_intelligence.domain.value_objects import ConversationId


class CapabilityExecutionUnavailableError(IntelligenceDomainError):
    """Raised when the capability execution bridge is not configured."""


@dataclass(frozen=True, slots=True)
class RequestCapabilityExecutionCommand:
    workspace_id: WorkspaceId
    conversation_id: str
    capability_id: str
    arguments: Mapping[str, object]
    permission_mode: str | None = None
    correlation_id: str | None = None


class RequestCapabilityExecution:
    """Conversation use case that submits work through the execution engine only."""

    def __init__(
        self,
        *,
        conversations,
        capability_execution: CapabilityExecutionPort | None,
    ) -> None:
        self._conversations = conversations
        self._capability_execution = capability_execution

    def execute(self, command: RequestCapabilityExecutionCommand) -> CapabilityExecutionView:
        if self._capability_execution is None:
            raise CapabilityExecutionUnavailableError(
                "Capability execution engine is not configured.",
            )

        # Raises ConversationNotFoundError when missing.
        self._conversations.get_conversation(
            ConversationId(command.conversation_id),
            workspace_id=command.workspace_id,
        )

        return self._capability_execution.submit(
            workspace_id=command.workspace_id,
            capability_id=command.capability_id,
            arguments=dict(command.arguments),
            conversation_id=command.conversation_id,
            correlation_id=command.correlation_id,
            permission_mode=command.permission_mode,
        )
