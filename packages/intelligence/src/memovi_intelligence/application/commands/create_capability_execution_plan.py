from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from memovi_shared import WorkspaceId

from memovi_intelligence.application.ports_capability_planner import (
    CapabilityPlannerPort,
    ExecutionPlanResultView,
    ExecutionPlanView,
)
from memovi_intelligence.application.services.conversation_service import ConversationService
from memovi_intelligence.domain.exceptions import IntelligenceDomainError
from memovi_intelligence.domain.value_objects import ConversationId


class CapabilityPlannerUnavailableError(IntelligenceDomainError):
    """Raised when the capability planner bridge is not configured."""


@dataclass(frozen=True, slots=True)
class CreateCapabilityExecutionPlanCommand:
    workspace_id: WorkspaceId
    conversation_id: str
    goal: str
    steps: Sequence[Mapping[str, object]]
    correlation_id: str | None = None
    metadata: Mapping[str, object] | None = None


@dataclass(frozen=True, slots=True)
class ExecuteCapabilityExecutionPlanCommand:
    workspace_id: WorkspaceId
    conversation_id: str
    goal: str
    steps: Sequence[Mapping[str, object]]
    correlation_id: str | None = None
    plan_id: str | None = None
    metadata: Mapping[str, object] | None = None


class CreateCapabilityExecutionPlan:
    """Conversation use case that builds a validated plan without executing it."""

    def __init__(
        self,
        *,
        conversations: ConversationService,
        capability_planner: CapabilityPlannerPort | None,
    ) -> None:
        self._conversations = conversations
        self._capability_planner = capability_planner

    def execute(self, command: CreateCapabilityExecutionPlanCommand) -> ExecutionPlanView:
        if self._capability_planner is None:
            raise CapabilityPlannerUnavailableError(
                "Capability planner is not configured.",
            )
        self._conversations.get_conversation(
            ConversationId(command.conversation_id),
            workspace_id=command.workspace_id,
        )
        return self._capability_planner.create_plan(
            workspace_id=command.workspace_id,
            goal=command.goal,
            steps=command.steps,
            conversation_id=command.conversation_id,
            correlation_id=command.correlation_id,
            metadata=command.metadata,
        )


class ExecuteCapabilityExecutionPlan:
    """Conversation use case that submits a validated plan through the engine."""

    def __init__(
        self,
        *,
        conversations: ConversationService,
        capability_planner: CapabilityPlannerPort | None,
    ) -> None:
        self._conversations = conversations
        self._capability_planner = capability_planner

    def execute(
        self,
        command: ExecuteCapabilityExecutionPlanCommand,
    ) -> ExecutionPlanResultView:
        if self._capability_planner is None:
            raise CapabilityPlannerUnavailableError(
                "Capability planner is not configured.",
            )
        self._conversations.get_conversation(
            ConversationId(command.conversation_id),
            workspace_id=command.workspace_id,
        )
        return self._capability_planner.execute_plan(
            workspace_id=command.workspace_id,
            goal=command.goal,
            steps=command.steps,
            conversation_id=command.conversation_id,
            correlation_id=command.correlation_id,
            plan_id=command.plan_id,
            metadata=command.metadata,
        )
