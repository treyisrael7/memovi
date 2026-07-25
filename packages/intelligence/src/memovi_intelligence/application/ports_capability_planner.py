"""Intelligence-facing ports for capability planning (no direct execution)."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol

from memovi_shared import WorkspaceId


@dataclass(frozen=True, slots=True)
class ExecutionStepView:
    step_id: str
    capability_id: str
    operation: str
    arguments: Mapping[str, object]
    dependencies: tuple[str, ...] = ()
    expected_result: str | None = None


@dataclass(frozen=True, slots=True)
class ExecutionPlanView:
    plan_id: str
    workspace_id: str
    goal: str
    steps: tuple[ExecutionStepView, ...]
    required_capabilities: tuple[str, ...]
    dependencies: tuple[tuple[str, str], ...]
    estimated_execution_count: int
    conversation_id: str | None
    correlation_id: str | None
    created_at: datetime
    metadata: Mapping[str, object] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ExecutionStepResultView:
    step_id: str
    capability_id: str
    operation: str
    execution_id: str | None
    status: str
    output: object | None = None
    error_code: str | None = None
    error_message: str | None = None
    duration: float = 0.0


@dataclass(frozen=True, slots=True)
class ExecutionPlanResultView:
    plan_id: str
    workspace_id: str
    status: str
    step_results: tuple[ExecutionStepResultView, ...]
    duration: float
    metadata: Mapping[str, object] = field(default_factory=dict)


class CapabilityPlannerPort(Protocol):
    """Bridge from Intelligence to the Capability Planner + plan execution.

    Intelligence creates and validates plans here. Execution of plan steps
    always flows through the Capability Execution Engine — never through
    direct capability calls.
    """

    def create_plan(
        self,
        *,
        workspace_id: WorkspaceId,
        goal: str,
        steps: Sequence[Mapping[str, object]],
        conversation_id: str | None = None,
        correlation_id: str | None = None,
        metadata: Mapping[str, object] | None = None,
    ) -> ExecutionPlanView:
        raise NotImplementedError

    def validate_plan(
        self,
        *,
        workspace_id: WorkspaceId,
        goal: str,
        steps: Sequence[Mapping[str, object]],
        conversation_id: str | None = None,
        correlation_id: str | None = None,
        plan_id: str | None = None,
        metadata: Mapping[str, object] | None = None,
    ) -> ExecutionPlanView:
        raise NotImplementedError

    def execute_plan(
        self,
        *,
        workspace_id: WorkspaceId,
        goal: str,
        steps: Sequence[Mapping[str, object]],
        conversation_id: str | None = None,
        correlation_id: str | None = None,
        plan_id: str | None = None,
        metadata: Mapping[str, object] | None = None,
    ) -> ExecutionPlanResultView:
        raise NotImplementedError
