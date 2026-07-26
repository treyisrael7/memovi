from collections.abc import Mapping, Sequence

from memovi_automation import (
    CapabilityPlanner,
    ExecutionPlan,
    ExecutionPlanResult,
    InvalidExecutionPlanError,
    PlanExecutionService,
)
from memovi_intelligence.application.ports_capability_planner import (
    ExecutionPlanResultView,
    ExecutionPlanView,
    ExecutionStepResultView,
    ExecutionStepView,
)
from memovi_intelligence.domain.exceptions import IntelligenceDomainError
from memovi_shared import WorkspaceId


class CapabilityPlannerBridgeError(IntelligenceDomainError):
    """Raised when the planner rejects an intelligence-facing request."""


class CapabilityPlannerAdapter:
    """Composition-root adapter: Intelligence planner port → automation planner/engine.

    Planning never executes capabilities. execute_plan submits steps only through
    PlanExecutionService → CapabilityExecutionEngine.
    """

    def __init__(
        self,
        *,
        planner: CapabilityPlanner,
        plan_execution: PlanExecutionService,
    ) -> None:
        self._planner = planner
        self._plan_execution = plan_execution

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
        try:
            plan = self._planner.create_plan(
                workspace_id=workspace_id,
                goal=goal,
                steps=steps,
                conversation_id=conversation_id,
                correlation_id=correlation_id,
                metadata=metadata,
            )
        except InvalidExecutionPlanError as exc:
            raise CapabilityPlannerBridgeError(str(exc)) from exc
        return _to_plan_view(plan)

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
        try:
            plan = self._planner.create_plan(
                workspace_id=workspace_id,
                goal=goal,
                steps=steps,
                conversation_id=conversation_id,
                correlation_id=correlation_id,
                plan_id=plan_id,
                metadata=metadata,
            )
        except InvalidExecutionPlanError as exc:
            raise CapabilityPlannerBridgeError(str(exc)) from exc
        return _to_plan_view(plan)

    def execute_plan(
        self,
        *,
        workspace_id: WorkspaceId,
        goal: str,
        steps: Sequence[Mapping[str, object]],
        caller_user_id: str,
        caller_session_id: str,
        caller_request_id: str,
        conversation_id: str | None = None,
        correlation_id: str | None = None,
        plan_id: str | None = None,
        metadata: Mapping[str, object] | None = None,
    ) -> ExecutionPlanResultView:
        from memovi_automation.domain.value_objects.authenticated_execution_context import (
            AuthenticatedExecutionContext,
        )

        try:
            plan = self._planner.create_plan(
                workspace_id=workspace_id,
                goal=goal,
                steps=steps,
                conversation_id=conversation_id,
                correlation_id=correlation_id,
                plan_id=plan_id,
                metadata=metadata,
            )
        except InvalidExecutionPlanError as exc:
            raise CapabilityPlannerBridgeError(str(exc)) from exc
        auth_context = AuthenticatedExecutionContext.create(
            user_id=caller_user_id,
            workspace_id=workspace_id,
            session_id=caller_session_id,
            request_id=caller_request_id,
            source="intelligence",
            conversation_id=conversation_id,
            correlation_id=correlation_id,
        )
        result = self._plan_execution.execute_plan(plan, context=auth_context)
        return _to_plan_result_view(result)


def _to_plan_view(plan: ExecutionPlan) -> ExecutionPlanView:
    return ExecutionPlanView(
        plan_id=plan.plan_id,
        workspace_id=plan.workspace_id,
        goal=plan.goal,
        steps=tuple(
            ExecutionStepView(
                step_id=step.step_id,
                capability_id=step.capability_id,
                operation=step.operation,
                arguments=dict(step.arguments),
                dependencies=step.dependency_step_ids,
                expected_result=step.expected_result,
            )
            for step in plan.steps
        ),
        required_capabilities=plan.required_capabilities,
        dependencies=plan.dependencies,
        estimated_execution_count=plan.estimated_execution_count,
        conversation_id=plan.conversation_id,
        correlation_id=plan.correlation_id,
        created_at=plan.created_at,
        metadata=dict(plan.metadata),
    )


def _to_plan_result_view(result: ExecutionPlanResult) -> ExecutionPlanResultView:
    return ExecutionPlanResultView(
        plan_id=result.plan_id,
        workspace_id=result.workspace_id,
        status=result.status,
        step_results=tuple(
            ExecutionStepResultView(
                step_id=step.step_id,
                capability_id=step.capability_id,
                operation=step.operation,
                execution_id=step.execution_id,
                status=step.status,
                output=step.output,
                error_code=step.error_code,
                error_message=step.error_message,
                duration=step.duration,
            )
            for step in result.step_results
        ),
        duration=result.duration,
        metadata=dict(result.metadata),
    )


__all__ = [
    "CapabilityPlannerAdapter",
    "CapabilityPlannerBridgeError",
]
