"""Immutable execution plan contracts for the Capability Planner.

Plans describe what should run and in what order. They never execute
capabilities — that remains the Capability Execution Engine's job.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from types import MappingProxyType
from uuid import UUID, uuid5

from memovi_shared import WorkspaceId

from memovi_automation.domain.exceptions import InvalidExecutionPlanError

# Stable namespace for content-derived plan ids (deterministic across identical requests).
_PLAN_ID_NAMESPACE = UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")


@dataclass(frozen=True, slots=True)
class ExecutionDependency:
    """Directed dependency from one step onto a prior step."""

    step_id: str
    # Reserved for future conditional/loop semantics (success | completed | always).
    kind: str = "success"

    def __post_init__(self) -> None:
        step_id = self.step_id.strip()
        kind = self.kind.strip().lower() or "success"
        if not step_id:
            raise InvalidExecutionPlanError(
                "Execution dependency step_id is required.",
                code="invalid_dependency",
            )
        if kind not in {"success", "completed", "always"}:
            raise InvalidExecutionPlanError(
                f"Unsupported dependency kind '{self.kind}'.",
                code="invalid_dependency",
                details={"kind": self.kind},
            )
        object.__setattr__(self, "step_id", step_id)
        object.__setattr__(self, "kind", kind)


@dataclass(frozen=True, slots=True)
class ExecutionStep:
    """Single planned capability invocation. No side effects occur at plan time."""

    step_id: str
    capability_id: str
    operation: str
    arguments: Mapping[str, object] = field(default_factory=dict)
    dependencies: tuple[ExecutionDependency, ...] = ()
    expected_result: str | None = None
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        step_id = self.step_id.strip()
        capability_id = self.capability_id.strip()
        operation = self.operation.strip()
        if not step_id:
            raise InvalidExecutionPlanError(
                "Execution step id is required.",
                code="invalid_step",
            )
        if not capability_id:
            raise InvalidExecutionPlanError(
                "Execution step capability_id is required.",
                code="invalid_step",
                details={"step_id": step_id},
            )
        if not operation:
            raise InvalidExecutionPlanError(
                "Execution step operation is required.",
                code="invalid_step",
                details={"step_id": step_id},
            )
        if not isinstance(self.arguments, Mapping):
            raise InvalidExecutionPlanError(
                "Execution step arguments must be a mapping.",
                code="invalid_step",
                details={"step_id": step_id},
            )
        expected = None if self.expected_result is None else self.expected_result.strip()
        if self.expected_result is not None and not expected:
            raise InvalidExecutionPlanError(
                "Execution step expected_result cannot be blank when provided.",
                code="invalid_step",
                details={"step_id": step_id},
            )

        # Ensure operation is present in arguments for capability schema validation.
        merged = dict(self.arguments)
        if "operation" not in merged:
            merged["operation"] = operation
        elif str(merged["operation"]).strip() != operation:
            raise InvalidExecutionPlanError(
                "Execution step operation must match arguments['operation'].",
                code="invalid_step",
                details={
                    "step_id": step_id,
                    "operation": operation,
                    "arguments_operation": merged["operation"],
                },
            )

        object.__setattr__(self, "step_id", step_id)
        object.__setattr__(self, "capability_id", capability_id)
        object.__setattr__(self, "operation", operation)
        object.__setattr__(self, "arguments", MappingProxyType(merged))
        object.__setattr__(self, "dependencies", tuple(self.dependencies))
        object.__setattr__(self, "expected_result", expected)
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))

    @property
    def dependency_step_ids(self) -> tuple[str, ...]:
        return tuple(dep.step_id for dep in self.dependencies)


@dataclass(frozen=True, slots=True)
class ExecutionPlan:
    """Deterministic, ordered capability execution plan."""

    plan_id: str
    workspace_id: str
    goal: str
    steps: tuple[ExecutionStep, ...]
    required_capabilities: tuple[str, ...] = ()
    dependencies: tuple[tuple[str, str], ...] = ()
    estimated_execution_count: int = 0
    conversation_id: str | None = None
    correlation_id: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        plan_id = self.plan_id.strip()
        workspace_id = self.workspace_id.strip()
        goal = self.goal.strip()
        if not plan_id:
            raise InvalidExecutionPlanError("Execution plan id is required.")
        if not workspace_id:
            raise InvalidExecutionPlanError("Execution plan workspace_id is required.")
        if not goal:
            raise InvalidExecutionPlanError("Execution plan goal is required.")
        if not self.steps:
            raise InvalidExecutionPlanError(
                "Execution plan must contain at least one step.",
                code="empty_plan",
            )
        if self.estimated_execution_count < 0:
            raise InvalidExecutionPlanError(
                "estimated_execution_count cannot be negative.",
            )

        object.__setattr__(self, "plan_id", plan_id)
        object.__setattr__(self, "workspace_id", workspace_id)
        object.__setattr__(self, "goal", goal)
        object.__setattr__(self, "steps", tuple(self.steps))
        object.__setattr__(
            self,
            "required_capabilities",
            tuple(self.required_capabilities),
        )
        object.__setattr__(self, "dependencies", tuple(self.dependencies))
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))

    @property
    def step_ids(self) -> tuple[str, ...]:
        return tuple(step.step_id for step in self.steps)

    def step_map(self) -> dict[str, ExecutionStep]:
        return {step.step_id: step for step in self.steps}

    @classmethod
    def create(
        cls,
        *,
        workspace_id: WorkspaceId | str,
        goal: str,
        steps: Sequence[ExecutionStep],
        plan_id: str | None = None,
        conversation_id: str | None = None,
        correlation_id: str | None = None,
        metadata: Mapping[str, object] | None = None,
    ) -> ExecutionPlan:
        workspace = (
            workspace_id.value
            if isinstance(workspace_id, WorkspaceId)
            else str(workspace_id).strip()
        )
        ordered = tuple(steps)
        required = tuple(dict.fromkeys(step.capability_id for step in ordered))
        edges: list[tuple[str, str]] = []
        for step in ordered:
            for dep in step.dependencies:
                edges.append((dep.step_id, step.step_id))
        meta = {} if metadata is None else dict(metadata)
        resolved_plan_id = plan_id or _deterministic_plan_id(
            workspace_id=workspace,
            goal=goal,
            steps=ordered,
            conversation_id=conversation_id,
            correlation_id=correlation_id,
            metadata=meta,
        )
        return cls(
            plan_id=resolved_plan_id,
            workspace_id=workspace,
            goal=goal,
            steps=ordered,
            required_capabilities=required,
            dependencies=tuple(edges),
            estimated_execution_count=len(ordered),
            conversation_id=conversation_id,
            correlation_id=correlation_id,
            metadata=meta,
        )


def _deterministic_plan_id(
    *,
    workspace_id: str,
    goal: str,
    steps: Sequence[ExecutionStep],
    conversation_id: str | None,
    correlation_id: str | None,
    metadata: Mapping[str, object],
) -> str:
    """Derive a stable plan id from plan content so identical requests match."""
    payload = {
        "workspace_id": workspace_id,
        "goal": goal,
        "conversation_id": conversation_id,
        "correlation_id": correlation_id,
        "metadata": metadata,
        "steps": [
            {
                "step_id": step.step_id,
                "capability_id": step.capability_id,
                "operation": step.operation,
                "arguments": dict(step.arguments),
                "dependencies": [
                    {"step_id": dep.step_id, "kind": dep.kind} for dep in step.dependencies
                ],
                "expected_result": step.expected_result,
                "metadata": dict(step.metadata),
            }
            for step in steps
        ],
    }
    encoded = json.dumps(payload, sort_keys=True, default=str, separators=(",", ":"))
    return str(uuid5(_PLAN_ID_NAMESPACE, encoded))


@dataclass(frozen=True, slots=True)
class ExecutionStepResult:
    """Outcome of one planned step after engine submission."""

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
class ExecutionPlanResult:
    """Aggregate result of submitting a validated plan to the execution engine."""

    plan_id: str
    workspace_id: str
    status: str
    step_results: tuple[ExecutionStepResult, ...] = ()
    duration: float = 0.0
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))
        object.__setattr__(self, "step_results", tuple(self.step_results))
