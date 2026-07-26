"""Submit validated execution plans to the Capability Execution Engine.

This service is intentionally separate from CapabilityPlanner. The planner
never imports or calls this module's execution path in reverse — composition
roots wire both, Intelligence chooses when to execute.
"""

from __future__ import annotations

from time import perf_counter

from memovi_automation.application.services.capability_execution_engine import (
    CapabilityExecutionEngine,
)
from memovi_automation.application.services.capability_planner import CapabilityPlanner
from memovi_automation.domain.exceptions import InvalidCapabilityArgumentsError
from memovi_automation.domain.value_objects import (
    CapabilityExecutionRequest,
    CapabilityExecutionStatus,
)
from memovi_automation.domain.value_objects.authenticated_execution_context import (
    AuthenticatedExecutionContext,
)
from memovi_automation.domain.value_objects.execution_plan import (
    ExecutionPlan,
    ExecutionPlanResult,
    ExecutionStepResult,
)
from memovi_shared import WorkspaceId


class PlanExecutionService:
    """Execute a validated plan by submitting each step through the engine.

    Never calls Capability.execute or CapabilityInvoker.invoke directly.
    Respects pending approval — does not auto-approve.
    """

    def __init__(
        self,
        *,
        engine: CapabilityExecutionEngine,
        planner: CapabilityPlanner | None = None,
    ) -> None:
        self._engine = engine
        self._planner = planner or CapabilityPlanner(registry=engine.registry)

    @property
    def engine(self) -> CapabilityExecutionEngine:
        return self._engine

    def execute_plan(
        self,
        plan: ExecutionPlan,
        *,
        context: AuthenticatedExecutionContext,
    ) -> ExecutionPlanResult:
        """Validate then submit plan steps in order through the execution engine."""
        validated = self._planner.validate_plan(plan)
        started = perf_counter()
        workspace = WorkspaceId(validated.workspace_id)
        if context.workspace_id != workspace:
            raise InvalidCapabilityArgumentsError(
                "Authenticated execution context workspace_id must match the plan.",
            )
        step_results: list[ExecutionStepResult] = []
        plan_status = "completed"

        for step in validated.steps:
            request = CapabilityExecutionRequest.create(
                capability_id=step.capability_id,
                workspace_id=workspace,
                arguments=dict(step.arguments),
                conversation_id=validated.conversation_id,
                correlation_id=validated.correlation_id or validated.plan_id,
                source="capability_planner",
                metadata={
                    "plan_id": validated.plan_id,
                    "step_id": step.step_id,
                    "operation": step.operation,
                    "expected_result": step.expected_result,
                    **dict(step.metadata),
                },
            )
            result = self._engine.submit(request, context)
            step_results.append(
                ExecutionStepResult(
                    step_id=step.step_id,
                    capability_id=step.capability_id,
                    operation=step.operation,
                    execution_id=result.execution_id,
                    status=result.status.value,
                    output=result.output,
                    error_code=None if result.error is None else result.error.code,
                    error_message=None if result.error is None else result.error.message,
                    duration=result.duration,
                )
            )

            if result.status is CapabilityExecutionStatus.PENDING_APPROVAL:
                plan_status = "awaiting_approval"
                break
            if result.status is CapabilityExecutionStatus.CANCELLED:
                plan_status = "cancelled"
                break
            if result.status is CapabilityExecutionStatus.FAILED:
                plan_status = "failed"
                break
            if result.status is not CapabilityExecutionStatus.COMPLETED:
                plan_status = "failed"
                break

        return ExecutionPlanResult(
            plan_id=validated.plan_id,
            workspace_id=validated.workspace_id,
            status=plan_status,
            step_results=tuple(step_results),
            duration=perf_counter() - started,
            metadata={
                "goal": validated.goal,
                "required_capabilities": list(validated.required_capabilities),
                "estimated_execution_count": validated.estimated_execution_count,
                "executed_steps": len(step_results),
            },
        )
