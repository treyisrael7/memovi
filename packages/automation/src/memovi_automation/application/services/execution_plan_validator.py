"""Validate execution plans before any capability is invoked."""

from __future__ import annotations

from memovi_automation.application.services.argument_validation import (
    validate_capability_arguments,
)
from memovi_automation.application.services.capability_registry import CapabilityRegistry
from memovi_automation.domain.exceptions import (
    InvalidCapabilityArgumentsError,
    InvalidExecutionPlanError,
    UnknownCapabilityError,
)
from memovi_automation.domain.value_objects.execution_plan import ExecutionPlan


class ExecutionPlanValidator:
    """Structural + schema validation for deterministic execution plans.

    Rejects invalid plans before the Capability Execution Engine is involved.
    Never executes capabilities.
    """

    def __init__(self, *, registry: CapabilityRegistry) -> None:
        self._registry = registry

    @property
    def registry(self) -> CapabilityRegistry:
        return self._registry

    def validate(self, plan: ExecutionPlan) -> ExecutionPlan:
        """Validate ``plan`` and return it unchanged when valid."""
        self._validate_step_ids(plan)
        self._validate_dependency_graph(plan)
        for step in plan.steps:
            self._validate_step(step.capability_id, step.operation, step.arguments, step.step_id)
        return plan

    def _validate_step_ids(self, plan: ExecutionPlan) -> None:
        seen: set[str] = set()
        for step in plan.steps:
            if step.step_id in seen:
                raise InvalidExecutionPlanError(
                    f"Duplicate step id '{step.step_id}'.",
                    code="duplicate_step_id",
                    details={"step_id": step.step_id},
                )
            seen.add(step.step_id)

    def _validate_dependency_graph(self, plan: ExecutionPlan) -> None:
        index = {step.step_id: position for position, step in enumerate(plan.steps)}
        for step in plan.steps:
            for dep in step.dependencies:
                if dep.step_id not in index:
                    raise InvalidExecutionPlanError(
                        f"Step '{step.step_id}' depends on unknown step '{dep.step_id}'.",
                        code="unknown_dependency",
                        details={
                            "step_id": step.step_id,
                            "dependency": dep.step_id,
                        },
                    )
                if dep.step_id == step.step_id:
                    raise InvalidExecutionPlanError(
                        f"Step '{step.step_id}' cannot depend on itself.",
                        code="cyclic_dependency",
                        details={"step_id": step.step_id},
                    )
                # Ordered plans require dependencies to appear earlier (no cycles).
                if index[dep.step_id] >= index[step.step_id]:
                    raise InvalidExecutionPlanError(
                        f"Step '{step.step_id}' depends on '{dep.step_id}' which does not "
                        "precede it in the plan order.",
                        code="invalid_dependency_order",
                        details={
                            "step_id": step.step_id,
                            "dependency": dep.step_id,
                        },
                    )

    def _validate_step(
        self,
        capability_id: str,
        operation: str,
        arguments: dict[str, object] | object,
        step_id: str,
    ) -> None:
        try:
            capability = self._registry.get(capability_id)
        except UnknownCapabilityError as exc:
            raise InvalidExecutionPlanError(
                f"Unknown capability '{capability_id}' in step '{step_id}'.",
                code="unknown_capability",
                details={"step_id": step_id, "capability_id": capability_id},
            ) from exc

        supported = _supported_operations(capability)
        if supported is not None and operation not in supported:
            raise InvalidExecutionPlanError(
                f"Unsupported operation '{operation}' for capability '{capability_id}'.",
                code="unknown_operation",
                details={
                    "step_id": step_id,
                    "capability_id": capability_id,
                    "operation": operation,
                    "supported_operations": sorted(supported),
                },
            )

        metadata = capability.metadata()
        try:
            validate_capability_arguments(arguments, metadata)  # type: ignore[arg-type]
        except InvalidCapabilityArgumentsError as exc:
            raise InvalidExecutionPlanError(
                f"Invalid arguments for step '{step_id}': {exc}",
                code="invalid_arguments",
                details={
                    "step_id": step_id,
                    "capability_id": capability_id,
                    "operation": operation,
                },
            ) from exc


def _supported_operations(capability: object) -> frozenset[str] | None:
    """Return declared operations when a capability exposes them."""
    getter = getattr(capability, "supported_operations", None)
    if callable(getter):
        value = getter()
        if isinstance(value, (set, frozenset, tuple, list)):
            return frozenset(str(item) for item in value)
    attr = getattr(capability, "SUPPORTED_OPERATIONS", None)
    if isinstance(attr, (set, frozenset, tuple, list)):
        return frozenset(str(item) for item in attr)
    return None
