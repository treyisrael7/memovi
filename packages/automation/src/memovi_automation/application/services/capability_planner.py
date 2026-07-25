"""Capability Planner — plan construction only.

The planner selects capabilities, orders steps, resolves dependencies, and
validates plans. It never calls Capability.execute, CapabilityInvoker.invoke,
or CapabilityExecutionEngine.submit.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from memovi_automation.application.services.capability_registry import CapabilityRegistry
from memovi_automation.application.services.execution_plan_validator import (
    ExecutionPlanValidator,
)
from memovi_automation.domain.exceptions import InvalidExecutionPlanError
from memovi_automation.domain.value_objects.execution_plan import (
    ExecutionDependency,
    ExecutionPlan,
    ExecutionStep,
)
from memovi_shared import WorkspaceId


class CapabilityPlanner:
    """Build deterministic execution plans for the Intelligence layer.

    Responsibilities:
    - Capability selection (as expressed by step drafts)
    - Execution ordering
    - Dependency resolution
    - Plan validation

    Non-responsibilities:
    - Permissions, execution, progress, audit (Capability Execution Engine)
    - Capability business logic
    """

    def __init__(
        self,
        *,
        registry: CapabilityRegistry,
        validator: ExecutionPlanValidator | None = None,
    ) -> None:
        self._registry = registry
        self._validator = validator or ExecutionPlanValidator(registry=registry)

    @property
    def registry(self) -> CapabilityRegistry:
        return self._registry

    @property
    def validator(self) -> ExecutionPlanValidator:
        return self._validator

    def create_plan(
        self,
        *,
        workspace_id: WorkspaceId | str,
        goal: str,
        steps: Sequence[Mapping[str, Any] | ExecutionStep],
        conversation_id: str | None = None,
        correlation_id: str | None = None,
        plan_id: str | None = None,
        metadata: Mapping[str, object] | None = None,
    ) -> ExecutionPlan:
        """Create and validate an execution plan. Does not execute anything."""
        if not goal or not str(goal).strip():
            raise InvalidExecutionPlanError(
                "Execution plan goal is required.",
                code="missing_goal",
            )
        if not steps:
            raise InvalidExecutionPlanError(
                "Execution plan must contain at least one step.",
                code="empty_plan",
            )

        built_steps = tuple(
            step if isinstance(step, ExecutionStep) else self._build_step(step, index)
            for index, step in enumerate(steps)
        )
        plan = ExecutionPlan.create(
            workspace_id=workspace_id,
            goal=str(goal).strip(),
            steps=built_steps,
            plan_id=plan_id,
            conversation_id=conversation_id,
            correlation_id=correlation_id,
            metadata=metadata,
        )
        return self._validator.validate(plan)

    def validate_plan(self, plan: ExecutionPlan) -> ExecutionPlan:
        """Re-validate an existing plan without executing it."""
        return self._validator.validate(plan)

    def _build_step(self, draft: Mapping[str, Any], index: int) -> ExecutionStep:
        step_id = str(draft.get("step_id") or f"step-{index + 1}").strip()
        capability_id = draft.get("capability_id") or draft.get("capability")
        if not isinstance(capability_id, str) or not capability_id.strip():
            raise InvalidExecutionPlanError(
                f"Step '{step_id}' is missing capability_id.",
                code="invalid_step",
                details={"step_id": step_id},
            )

        arguments = draft.get("arguments")
        if arguments is None:
            arguments = {}
        if not isinstance(arguments, Mapping):
            raise InvalidExecutionPlanError(
                f"Step '{step_id}' arguments must be a mapping.",
                code="invalid_step",
                details={"step_id": step_id},
            )
        args = dict(arguments)

        operation = draft.get("operation")
        if operation is None:
            operation = args.get("operation")
        if not isinstance(operation, str) or not operation.strip():
            raise InvalidExecutionPlanError(
                f"Step '{step_id}' is missing operation.",
                code="invalid_step",
                details={"step_id": step_id},
            )
        operation = operation.strip()
        args.setdefault("operation", operation)

        dependencies = _parse_dependencies(draft.get("dependencies"), step_id=step_id)
        expected = draft.get("expected_result")
        meta = draft.get("metadata")
        if meta is not None and not isinstance(meta, Mapping):
            raise InvalidExecutionPlanError(
                f"Step '{step_id}' metadata must be a mapping.",
                code="invalid_step",
                details={"step_id": step_id},
            )

        return ExecutionStep(
            step_id=step_id,
            capability_id=capability_id.strip(),
            operation=operation,
            arguments=args,
            dependencies=dependencies,
            expected_result=None if expected is None else str(expected),
            metadata={} if meta is None else dict(meta),
        )


def _parse_dependencies(
    raw: object,
    *,
    step_id: str,
) -> tuple[ExecutionDependency, ...]:
    if raw is None:
        return ()
    if not isinstance(raw, (list, tuple)):
        raise InvalidExecutionPlanError(
            f"Step '{step_id}' dependencies must be an array.",
            code="invalid_dependency",
            details={"step_id": step_id},
        )
    parsed: list[ExecutionDependency] = []
    for item in raw:
        if isinstance(item, ExecutionDependency):
            parsed.append(item)
            continue
        if isinstance(item, str):
            parsed.append(ExecutionDependency(step_id=item))
            continue
        if isinstance(item, Mapping):
            dep_id = item.get("step_id") or item.get("depends_on")
            kind = item.get("kind", "success")
            if not isinstance(dep_id, str):
                raise InvalidExecutionPlanError(
                    f"Step '{step_id}' has an invalid dependency entry.",
                    code="invalid_dependency",
                    details={"step_id": step_id},
                )
            parsed.append(
                ExecutionDependency(
                    step_id=dep_id,
                    kind=str(kind) if kind is not None else "success",
                )
            )
            continue
        raise InvalidExecutionPlanError(
            f"Step '{step_id}' has an invalid dependency entry.",
            code="invalid_dependency",
            details={"step_id": step_id},
        )
    return tuple(parsed)
