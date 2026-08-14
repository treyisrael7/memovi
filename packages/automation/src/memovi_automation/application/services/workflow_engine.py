"""Workflow Engine — orchestrate reusable workflows through planner + engine.

Ownership:
- WorkflowEngine: definition lookup, variable binding, sequential step orchestration
- CapabilityPlanner: materialize each step into a validated ExecutionPlan
- PlanExecutionService → CapabilityExecutionEngine: permissions, invoke, audit

Never calls Capability.execute or CapabilityInvoker.invoke directly.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from threading import Lock
from time import perf_counter
from typing import cast

from memovi_observability import get_logger, get_metrics_recorder, get_request_context
from memovi_observability.logging.structured import log_operation
from memovi_shared import WorkspaceId

from memovi_automation.application.ports_workflow import WorkflowHistoryStore, WorkflowLibrary
from memovi_automation.application.services.capability_planner import CapabilityPlanner
from memovi_automation.application.services.plan_execution_service import PlanExecutionService
from memovi_automation.application.services.workflow_validator import WorkflowValidator
from memovi_automation.domain.exceptions import (
    CapabilityExecutionNotFoundError,
    InvalidExecutionPlanError,
    InvalidWorkflowError,
    UnknownWorkflowError,
)
from memovi_automation.domain.value_objects.authenticated_execution_context import (
    AuthenticatedExecutionContext,
)
from memovi_automation.domain.value_objects.capability_execution_result import (
    CapabilityExecutionResult,
)
from memovi_automation.domain.value_objects.capability_execution_status import (
    CapabilityExecutionStatus,
)
from memovi_automation.domain.value_objects.execution_plan import ExecutionPlan
from memovi_automation.domain.value_objects.workflow import (
    WorkflowContext,
    WorkflowDefinition,
    WorkflowExecutionResult,
    WorkflowHistoryEntry,
    WorkflowInstance,
    WorkflowStep,
    WorkflowStepResult,
    read_output_path,
    substitute_value,
)

LOGGER = get_logger("memovi.automation.workflow")

_INTERRUPT_REASON = "Workflow interrupted by application restart."


class WorkflowEngine:
    """Execute reusable workflows as sequential planner-backed capability plans."""

    def __init__(
        self,
        *,
        library: WorkflowLibrary,
        planner: CapabilityPlanner,
        plan_execution: PlanExecutionService,
        history: WorkflowHistoryStore,
        validator: WorkflowValidator | None = None,
        recover_on_init: bool = False,
    ) -> None:
        self._library = library
        self._planner = planner
        self._plan_execution = plan_execution
        self._history = history
        self._validator = validator or WorkflowValidator(registry=planner.registry)
        self._instance_locks_guard = Lock()
        self._instance_locks: dict[str, Lock] = {}
        if recover_on_init:
            self.recover_interrupted_workflows()
            self.recover_awaiting_approvals()

    @property
    def library(self) -> WorkflowLibrary:
        return self._library

    @property
    def history(self) -> WorkflowHistoryStore:
        return self._history

    @property
    def planner(self) -> CapabilityPlanner:
        return self._planner

    def get_workflow(self, workflow_id: str) -> WorkflowDefinition:
        try:
            definition = self._library.get(workflow_id)
        except UnknownWorkflowError:
            raise
        except Exception as exc:  # pragma: no cover - library contract
            raise UnknownWorkflowError(
                f"Unknown workflow '{workflow_id}'.",
                workflow_id=workflow_id,
            ) from exc
        return self._validator.validate_definition(definition)

    def list_workflows(self) -> tuple[WorkflowDefinition, ...]:
        """List workflows whose required capabilities are currently registered."""
        available: list[WorkflowDefinition] = []
        for item in self._library.list():
            try:
                available.append(self._validator.validate_definition(item))
            except InvalidWorkflowError as exc:
                if exc.code == "unknown_capability":
                    continue
                raise
        return tuple(available)

    def recover_interrupted_workflows(self) -> tuple[WorkflowExecutionResult, ...]:
        """Mark interrupted ``running`` workflows failed without re-executing steps.

        ``awaiting_approval`` rows are left intact so pending capability
        approvals can continue through the Capability Execution Engine after
        restart. Call ``recover_awaiting_approvals`` afterward to continue
        workflows whose waiting capability already finished.
        """
        recovered = self._history.fail_interrupted_executions(reason=_INTERRUPT_REASON)
        if recovered:
            log_operation(
                LOGGER,
                operation="workflow.recover",
                status="success",
                recovered_count=len(recovered),
            )
        return recovered

    def recover_awaiting_approvals(self) -> tuple[WorkflowExecutionResult, ...]:
        """Continue workflows waiting on a capability that already finished.

        Used after process restart when approval was recorded but remaining
        workflow steps had not run yet. Still-pending approvals are left intact.
        """
        resumed: list[WorkflowExecutionResult] = []
        for stored in self._history.list_by_status(status="awaiting_approval"):
            pending = next(
                (
                    step
                    for step in stored.step_results
                    if step.status == "pending_approval" and step.execution_id
                ),
                None,
            )
            execution_id = pending.execution_id if pending is not None else None
            if execution_id is None:
                last = stored.step_results[-1] if stored.step_results else None
                execution_id = last.execution_id if last is not None else None
            if not execution_id:
                continue
            auth_context = _auth_context_from_result(stored)
            if auth_context is None:
                continue
            try:
                capability = self._plan_execution.engine.get(
                    execution_id,
                    workspace_id=WorkspaceId(stored.workspace_id),
                )
            except CapabilityExecutionNotFoundError:
                continue
            if capability.status is CapabilityExecutionStatus.PENDING_APPROVAL:
                continue
            continued = self.resume_after_capability(
                execution_id=execution_id,
                workspace_id=stored.workspace_id,
                auth_context=auth_context,
            )
            if continued is not None:
                resumed.append(continued)
        return tuple(resumed)

    def resume_after_capability(
        self,
        *,
        execution_id: str,
        workspace_id: WorkspaceId | str,
        auth_context: AuthenticatedExecutionContext,
    ) -> WorkflowExecutionResult | None:
        """Continue a paused workflow after its waiting capability is decided.

        Does not resubmit the approved/denied capability. Returns ``None`` when
        the execution is not part of a workflow instance.
        """
        workspace = (
            workspace_id.value
            if isinstance(workspace_id, WorkspaceId)
            else str(workspace_id).strip()
        )
        try:
            capability = self._plan_execution.engine.get(
                execution_id,
                workspace_id=WorkspaceId(workspace),
            )
        except CapabilityExecutionNotFoundError:
            return None
        instance_id = _meta_str(capability.metadata, "workflow_instance_id")
        if instance_id is None:
            return None
        with self._lock_for(instance_id):
            return self._resume_locked(
                capability=capability,
                workspace=workspace,
                auth_context=auth_context,
            )

    def materialize_plan(
        self,
        *,
        workflow_id: str,
        workspace_id: WorkspaceId | str,
        variables: Mapping[str, object] | None = None,
        conversation_id: str | None = None,
        correlation_id: str | None = None,
    ) -> ExecutionPlan:
        """Build a validated ExecutionPlan when all inputs resolve from variables.

        Steps that reference prior step outputs cannot be fully materialized
        ahead of execution; use ``execute`` for those workflows.
        """
        definition = self.get_workflow(workflow_id)
        context = self._validator.validate_variables(definition, variables)
        for step in definition.steps:
            refs = _step_output_refs(step.input_mapping)
            if refs:
                raise InvalidWorkflowError(
                    f"Step '{step.step_id}' depends on prior step outputs; "
                    "materialize_plan requires variable-only inputs.",
                    code="requires_sequential_execution",
                    details={"step_id": step.step_id, "references": list(refs)},
                )

        drafts = []
        prior_ids: list[str] = []
        for step in definition.steps:
            arguments = dict(
                cast(
                    Mapping[str, object],
                    substitute_value(dict(step.input_mapping), context),
                )
            )
            arguments.setdefault("operation", step.operation)
            drafts.append(
                {
                    "step_id": step.step_id,
                    "capability_id": step.capability_id,
                    "operation": step.operation,
                    "arguments": arguments,
                    "dependencies": list(prior_ids),
                    "expected_result": step.expected_result,
                    "metadata": {
                        "workflow_id": definition.workflow_id,
                        "workflow_step": step.step_id,
                    },
                }
            )
            prior_ids = [step.step_id]

        try:
            return self._planner.create_plan(
                workspace_id=workspace_id,
                goal=definition.name,
                steps=drafts,
                conversation_id=conversation_id,
                correlation_id=correlation_id,
                metadata={
                    "workflow_id": definition.workflow_id,
                    "source": "workflow_engine",
                },
            )
        except InvalidExecutionPlanError as exc:
            raise InvalidWorkflowError(
                str(exc),
                code=getattr(exc, "code", "invalid_execution_plan"),
                details=getattr(exc, "details", None),
            ) from exc

    def execute(
        self,
        *,
        workflow_id: str,
        workspace_id: WorkspaceId | str,
        auth_context: AuthenticatedExecutionContext,
        variables: Mapping[str, object] | None = None,
        conversation_id: str | None = None,
        correlation_id: str | None = None,
        metadata: Mapping[str, object] | None = None,
    ) -> WorkflowExecutionResult:
        """Validate, plan each step through the planner, execute via the engine."""
        definition = self.get_workflow(workflow_id)
        context = self._validator.validate_variables(definition, variables)
        workspace = (
            workspace_id.value
            if isinstance(workspace_id, WorkspaceId)
            else str(workspace_id).strip()
        )
        if auth_context.workspace_id.value != workspace:
            raise InvalidWorkflowError(
                "Authenticated execution context workspace_id must match the workflow.",
                code="workspace_mismatch",
            )
        request_context = get_request_context()
        request_id = None if request_context is None else request_context.request_id
        resolved_correlation = (
            correlation_id
            or (None if request_context is None else request_context.correlation_id)
            or request_id
        )
        run_metadata = {} if metadata is None else dict(metadata)
        if request_id is not None:
            run_metadata.setdefault("request_id", request_id)
        run_metadata.setdefault("user_id", auth_context.user_id)
        run_metadata.setdefault("session_id", auth_context.session_id)
        run_metadata.setdefault("request_id", auth_context.request_id)

        instance = WorkflowInstance.create(
            workflow=definition,
            workspace_id=workspace,
            context=context,
            conversation_id=conversation_id,
            correlation_id=resolved_correlation,
            metadata=run_metadata,
        )
        started_at = datetime.now(UTC)

        log_operation(
            LOGGER,
            operation="workflow.execute.start",
            status="started",
            workflow_id=definition.workflow_id,
            workflow_instance_id=instance.instance_id,
            workspace_id=workspace,
            step_count=len(definition.steps),
        )

        # Persist running state early so restarts can detect interrupted work.
        self._persist_progress(
            instance_id=instance.instance_id,
            definition=definition,
            workspace=workspace,
            status="running",
            completed=[],
            failed=[],
            step_results=[],
            errors=[],
            audit_refs=[],
            outputs={},
            started_at=started_at,
            finished_at=None,
            duration=0.0,
            context=context,
            run_metadata=run_metadata,
            conversation_id=conversation_id,
        )

        with self._lock_for(instance.instance_id):
            return self._continue_steps(
                definition=definition,
                workspace=workspace,
                auth_context=auth_context,
                instance_id=instance.instance_id,
                conversation_id=conversation_id,
                correlation_id=instance.correlation_id,
                request_id=request_id or auth_context.request_id,
                run_metadata=run_metadata,
                context=context,
                started_at=started_at,
                step_results=[],
                completed=[],
                failed=[],
                errors=[],
                audit_refs=[],
                start_index=0,
            )

    def _lock_for(self, instance_id: str) -> Lock:
        with self._instance_locks_guard:
            lock = self._instance_locks.get(instance_id)
            if lock is None:
                lock = Lock()
                self._instance_locks[instance_id] = lock
            return lock

    def _resume_locked(
        self,
        *,
        capability: CapabilityExecutionResult,
        workspace: str,
        auth_context: AuthenticatedExecutionContext,
    ) -> WorkflowExecutionResult | None:
        instance_id = _meta_str(capability.metadata, "workflow_instance_id")
        if instance_id is None:
            return None
        stored = self._history.get_result(
            instance_id,
            workspace_id=WorkspaceId(workspace),
        )
        if stored is None:
            return None
        if stored.status != "awaiting_approval":
            return stored

        definition = self.get_workflow(stored.workflow_id)
        waiting_index = next(
            (
                index
                for index, step in enumerate(stored.step_results)
                if step.execution_id == capability.execution_id
            ),
            None,
        )
        if waiting_index is None:
            return stored

        context = _context_from_result(stored)
        step_results = list(stored.step_results)
        completed = list(stored.completed_steps)
        failed = list(stored.failed_steps)
        errors = list(stored.errors)
        audit_refs = list(stored.audit_references)
        waiting = step_results[waiting_index]
        definition_step = definition.steps[waiting_index]
        run_metadata = dict(stored.metadata)
        run_metadata["resumed_from_approval"] = True
        conversation_id = _meta_str(stored.metadata, "conversation_id")

        if waiting.status == "pending_approval":
            updated = _workflow_step_from_capability(
                step=definition_step,
                plan_id=waiting.plan_id,
                execution=capability,
            )
            step_results[waiting_index] = updated
            if capability.status is CapabilityExecutionStatus.COMPLETED:
                if definition_step.step_id not in completed:
                    completed.append(definition_step.step_id)
                context = _bind_completed_step(definition_step, capability.output, context)
            elif capability.status is CapabilityExecutionStatus.CANCELLED:
                if definition_step.step_id not in failed:
                    failed.append(definition_step.step_id)
                if updated.error_message:
                    errors.append(updated.error_message)
                return self._finish(
                    definition=definition,
                    workspace=workspace,
                    instance_id=instance_id,
                    status="cancelled",
                    completed=completed,
                    failed=failed,
                    step_results=step_results,
                    errors=errors,
                    audit_refs=audit_refs,
                    context=context,
                    started_at=stored.started_at,
                    run_metadata=run_metadata,
                    conversation_id=conversation_id,
                    correlation_id=_meta_str(stored.metadata, "correlation_id"),
                )
            else:
                if definition_step.step_id not in failed:
                    failed.append(definition_step.step_id)
                if updated.error_message:
                    errors.append(updated.error_message)
                return self._finish(
                    definition=definition,
                    workspace=workspace,
                    instance_id=instance_id,
                    status="failed",
                    completed=completed,
                    failed=failed,
                    step_results=step_results,
                    errors=errors,
                    audit_refs=audit_refs,
                    context=context,
                    started_at=stored.started_at,
                    run_metadata=run_metadata,
                    conversation_id=conversation_id,
                    correlation_id=_meta_str(stored.metadata, "correlation_id"),
                )
            self._persist_progress(
                instance_id=instance_id,
                definition=definition,
                workspace=workspace,
                status=(
                    "awaiting_approval" if waiting_index + 1 < len(definition.steps) else "running"
                ),
                completed=completed,
                failed=failed,
                step_results=step_results,
                errors=errors,
                audit_refs=audit_refs,
                outputs=_collect_outputs(definition, context),
                started_at=stored.started_at,
                finished_at=None,
                duration=_elapsed(stored.started_at),
                context=context,
                run_metadata=run_metadata,
                conversation_id=conversation_id,
            )

        return self._continue_steps(
            definition=definition,
            workspace=workspace,
            auth_context=auth_context,
            instance_id=instance_id,
            conversation_id=conversation_id,
            correlation_id=_meta_str(stored.metadata, "correlation_id") or instance_id,
            request_id=auth_context.request_id,
            run_metadata=run_metadata,
            context=context,
            started_at=stored.started_at,
            step_results=step_results,
            completed=completed,
            failed=failed,
            errors=errors,
            audit_refs=audit_refs,
            start_index=waiting_index + 1,
        )

    def _continue_steps(
        self,
        *,
        definition: WorkflowDefinition,
        workspace: str,
        auth_context: AuthenticatedExecutionContext,
        instance_id: str,
        conversation_id: str | None,
        correlation_id: str,
        request_id: str | None,
        run_metadata: Mapping[str, object],
        context: WorkflowContext,
        started_at: datetime,
        step_results: list[WorkflowStepResult],
        completed: list[str],
        failed: list[str],
        errors: list[str],
        audit_refs: list[str],
        start_index: int,
    ) -> WorkflowExecutionResult:
        status = "completed"
        metadata = dict(run_metadata)

        for step in definition.steps[start_index:]:
            step_started = perf_counter()
            try:
                arguments = {
                    key: value
                    for key, value in dict(
                        cast(
                            Mapping[str, object],
                            substitute_value(dict(step.input_mapping), context),
                        )
                    ).items()
                    if value is not None
                }
                arguments.setdefault("operation", step.operation)
                step_meta: dict[str, object] = {
                    "workflow_id": definition.workflow_id,
                    "workflow_instance_id": instance_id,
                    "workflow_step": step.step_id,
                }
                if request_id is not None:
                    step_meta["request_id"] = request_id
                plan = self._planner.create_plan(
                    workspace_id=workspace,
                    goal=f"{definition.name}: {step.step_id}",
                    steps=[
                        {
                            "step_id": step.step_id,
                            "capability_id": step.capability_id,
                            "operation": step.operation,
                            "arguments": arguments,
                            "expected_result": step.expected_result,
                            "metadata": step_meta,
                        }
                    ],
                    conversation_id=conversation_id,
                    correlation_id=correlation_id,
                    metadata={
                        "workflow_id": definition.workflow_id,
                        "workflow_instance_id": instance_id,
                        "source": "workflow_engine",
                        **({"request_id": request_id} if request_id is not None else {}),
                    },
                )
            except (InvalidExecutionPlanError, InvalidWorkflowError) as exc:
                failed.append(step.step_id)
                errors.append(str(exc))
                step_results.append(
                    WorkflowStepResult(
                        step_id=step.step_id,
                        capability_id=step.capability_id,
                        operation=step.operation,
                        execution_id=None,
                        status="failed",
                        error_code=getattr(exc, "code", "invalid_workflow"),
                        error_message=str(exc),
                    )
                )
                status = "failed"
                log_operation(
                    LOGGER,
                    operation="workflow.step.execute",
                    status="error",
                    duration_ms=(perf_counter() - step_started) * 1000,
                    workflow_id=definition.workflow_id,
                    workflow_instance_id=instance_id,
                    step_id=step.step_id,
                    capability_id=step.capability_id,
                    error=str(exc),
                )
                break

            plan_result = self._plan_execution.execute_plan(plan, context=auth_context)
            plan_step = plan_result.step_results[0] if plan_result.step_results else None
            if plan_step is None:
                failed.append(step.step_id)
                errors.append("Plan execution returned no step results.")
                status = "failed"
                log_operation(
                    LOGGER,
                    operation="workflow.step.execute",
                    status="error",
                    duration_ms=(perf_counter() - step_started) * 1000,
                    workflow_id=definition.workflow_id,
                    workflow_instance_id=instance_id,
                    step_id=step.step_id,
                    capability_id=step.capability_id,
                    plan_id=plan.plan_id,
                    error="Plan execution returned no step results.",
                )
                break

            step_result = WorkflowStepResult(
                step_id=step.step_id,
                capability_id=step.capability_id,
                operation=step.operation,
                execution_id=plan_step.execution_id,
                status=plan_step.status,
                output=plan_step.output,
                error_code=plan_step.error_code,
                error_message=plan_step.error_message,
                duration=plan_step.duration,
                plan_id=plan.plan_id,
            )
            step_results.append(step_result)
            if plan_step.execution_id:
                audit_refs.append(plan_step.execution_id)

            step_log_status = {
                "completed": "success",
                "pending_approval": "awaiting_approval",
                "failed": "error",
                "cancelled": "cancelled",
            }.get(plan_step.status, plan_step.status)
            log_operation(
                LOGGER,
                operation="workflow.step.execute",
                status=step_log_status,
                duration_ms=(perf_counter() - step_started) * 1000,
                workflow_id=definition.workflow_id,
                workflow_instance_id=instance_id,
                step_id=step.step_id,
                capability_id=step.capability_id,
                plan_id=plan.plan_id,
                execution_id=plan_step.execution_id,
                error=plan_step.error_message,
            )

            if plan_result.status == "awaiting_approval":
                status = "awaiting_approval"
                break
            if plan_result.status == "cancelled":
                status = "cancelled"
                failed.append(step.step_id)
                if plan_step.error_message:
                    errors.append(plan_step.error_message)
                break
            if plan_result.status != "completed" or plan_step.status != "completed":
                status = "failed"
                failed.append(step.step_id)
                if plan_step.error_message:
                    errors.append(plan_step.error_message)
                break

            completed.append(step.step_id)
            context = _bind_completed_step(step, plan_step.output, context)
            self._persist_progress(
                instance_id=instance_id,
                definition=definition,
                workspace=workspace,
                status="running",
                completed=completed,
                failed=failed,
                step_results=step_results,
                errors=errors,
                audit_refs=audit_refs,
                outputs=_collect_outputs(definition, context),
                started_at=started_at,
                finished_at=None,
                duration=_elapsed(started_at),
                context=context,
                run_metadata=metadata,
                conversation_id=conversation_id,
            )

        return self._finish(
            definition=definition,
            workspace=workspace,
            instance_id=instance_id,
            status=status,
            completed=completed,
            failed=failed,
            step_results=step_results,
            errors=errors,
            audit_refs=audit_refs,
            context=context,
            started_at=started_at,
            run_metadata=metadata,
            conversation_id=conversation_id,
            correlation_id=correlation_id,
        )

    def _finish(
        self,
        *,
        definition: WorkflowDefinition,
        workspace: str,
        instance_id: str,
        status: str,
        completed: list[str],
        failed: list[str],
        step_results: list[WorkflowStepResult],
        errors: list[str],
        audit_refs: list[str],
        context: WorkflowContext,
        started_at: datetime,
        run_metadata: Mapping[str, object],
        conversation_id: str | None,
        correlation_id: str | None,
    ) -> WorkflowExecutionResult:
        finished_at = datetime.now(UTC)
        result = WorkflowExecutionResult(
            instance_id=instance_id,
            workflow_id=definition.workflow_id,
            workflow_name=definition.name,
            workspace_id=workspace,
            status=status,
            completed_steps=tuple(completed),
            failed_steps=tuple(failed),
            step_results=tuple(step_results),
            duration=_elapsed(started_at),
            outputs=_collect_outputs(definition, context),
            errors=tuple(errors),
            audit_references=tuple(audit_refs),
            started_at=started_at,
            finished_at=finished_at,
            metadata={
                "required_capabilities": list(definition.required_capabilities),
                "conversation_id": conversation_id,
                "correlation_id": correlation_id,
                **_with_resume_context(run_metadata, context),
            },
        )
        log_operation(
            LOGGER,
            operation="workflow.execute.finish",
            status="success" if status == "completed" else status,
            duration_ms=result.duration * 1000,
            workflow_id=definition.workflow_id,
            workflow_instance_id=instance_id,
            workspace_id=workspace,
            completed_steps=len(completed),
            failed_steps=len(failed),
        )
        self._record_history(result, context)
        self._record_metrics(result)
        return result

    def _persist_progress(
        self,
        *,
        instance_id: str,
        definition: WorkflowDefinition,
        workspace: str,
        status: str,
        completed: list[str],
        failed: list[str],
        step_results: list[WorkflowStepResult],
        errors: list[str],
        audit_refs: list[str],
        outputs: Mapping[str, object],
        started_at: datetime,
        finished_at: datetime | None,
        duration: float,
        context: WorkflowContext,
        run_metadata: Mapping[str, object],
        conversation_id: str | None,
    ) -> None:
        result = WorkflowExecutionResult(
            instance_id=instance_id,
            workflow_id=definition.workflow_id,
            workflow_name=definition.name,
            workspace_id=workspace,
            status=status,
            completed_steps=tuple(completed),
            failed_steps=tuple(failed),
            step_results=tuple(step_results),
            duration=duration,
            outputs=dict(outputs),
            errors=tuple(errors),
            audit_references=tuple(audit_refs),
            started_at=started_at,
            finished_at=finished_at,
            metadata={
                "required_capabilities": list(definition.required_capabilities),
                "conversation_id": conversation_id,
                **_with_resume_context(run_metadata, context),
            },
        )
        self._history.store_result(result)
        # Keep summary row aligned for history list views during long runs.
        entry = WorkflowHistoryEntry(
            instance_id=result.instance_id,
            workflow_id=result.workflow_id,
            workflow_name=result.workflow_name,
            workspace_id=result.workspace_id,
            status=result.status,
            executed_at=result.started_at,
            duration=result.duration,
            result_summary={
                "status": result.status,
                "completed_steps": list(result.completed_steps),
                "failed_steps": list(result.failed_steps),
                "outputs": dict(result.outputs),
                "errors": list(result.errors),
                "variables": dict(context.variables),
            },
            executed_capabilities=tuple(
                dict.fromkeys(
                    step.capability_id
                    for step in result.step_results
                    if step.execution_id is not None
                )
            ),
            audit_references=result.audit_references,
            user_id=_meta_str(run_metadata, "user_id"),
            completed_at=result.finished_at,
            executed_steps=result.completed_steps,
            failed_steps=result.failed_steps,
            error_details=result.errors,
        )
        self._history.append(entry)

    def _record_history(
        self,
        result: WorkflowExecutionResult,
        context: WorkflowContext,
    ) -> None:
        capabilities = tuple(
            dict.fromkeys(
                step.capability_id for step in result.step_results if step.execution_id is not None
            )
        )
        entry = WorkflowHistoryEntry(
            instance_id=result.instance_id,
            workflow_id=result.workflow_id,
            workflow_name=result.workflow_name,
            workspace_id=result.workspace_id,
            status=result.status,
            executed_at=result.started_at,
            duration=result.duration,
            result_summary={
                "status": result.status,
                "completed_steps": list(result.completed_steps),
                "failed_steps": list(result.failed_steps),
                "outputs": dict(result.outputs),
                "errors": list(result.errors),
                "variables": dict(context.variables),
            },
            executed_capabilities=capabilities,
            audit_references=result.audit_references,
            user_id=_meta_str(result.metadata, "user_id"),
            completed_at=result.finished_at,
            executed_steps=result.completed_steps,
            failed_steps=result.failed_steps,
            error_details=result.errors,
        )
        self._history.append(entry)
        self._history.store_result(result)

    def _record_metrics(self, result: WorkflowExecutionResult) -> None:
        metrics = get_metrics_recorder()
        metrics.timing(
            "memovi.workflows.execution.duration_ms",
            result.duration * 1000,
            tags={"status": result.status, "workflow_id": result.workflow_id},
        )
        if result.status == "completed":
            metrics.increment(
                "memovi.workflows.execution.completed",
                tags={"workflow_id": result.workflow_id},
            )
        elif result.status == "failed":
            metrics.increment(
                "memovi.workflows.execution.failed",
                tags={"workflow_id": result.workflow_id},
            )
        elif result.status == "cancelled":
            metrics.increment(
                "memovi.workflows.execution.cancelled",
                tags={"workflow_id": result.workflow_id},
            )
        elif result.status == "awaiting_approval":
            metrics.increment(
                "memovi.workflows.execution.awaiting_approval",
                tags={"workflow_id": result.workflow_id},
            )


def _meta_str(metadata: Mapping[str, object], key: str) -> str | None:
    value = metadata.get(key)
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _elapsed(started_at: datetime) -> float:
    return max(0.0, (datetime.now(UTC) - started_at).total_seconds())


def _with_resume_context(
    run_metadata: Mapping[str, object],
    context: WorkflowContext,
) -> dict[str, object]:
    return {
        **dict(run_metadata),
        "resume_context": {
            "variables": dict(context.variables),
            "step_outputs": dict(context.step_outputs),
        },
    }


def _context_from_result(result: WorkflowExecutionResult) -> WorkflowContext:
    stored = result.metadata.get("resume_context")
    if isinstance(stored, Mapping):
        variables = stored.get("variables")
        outputs = stored.get("step_outputs")
        return WorkflowContext(
            variables=dict(variables) if isinstance(variables, Mapping) else {},
            step_outputs=dict(outputs) if isinstance(outputs, Mapping) else {},
        )
    variables: dict[str, object] = {}
    summary = result.metadata.get("variables")
    if isinstance(summary, Mapping):
        variables = dict(summary)
    step_outputs: dict[str, object] = {}
    for step in result.step_results:
        if step.status == "completed":
            step_outputs[step.step_id] = step.output
    return WorkflowContext(variables=variables, step_outputs=step_outputs)


def _bind_completed_step(
    step: WorkflowStep,
    output: object,
    context: WorkflowContext,
) -> WorkflowContext:
    context = context.with_step_output(step.step_id, output)
    if step.output_mapping:
        bindings = {
            name: read_output_path(output, path) for name, path in step.output_mapping.items()
        }
        context = context.with_bound_values(bindings)
    return context


def _workflow_step_from_capability(
    *,
    step: WorkflowStep,
    plan_id: str | None,
    execution: CapabilityExecutionResult,
) -> WorkflowStepResult:
    error = execution.error
    return WorkflowStepResult(
        step_id=step.step_id,
        capability_id=step.capability_id,
        operation=step.operation,
        execution_id=execution.execution_id,
        status=execution.status.value,
        output=execution.output,
        error_code=None if error is None else error.code,
        error_message=None if error is None else error.message,
        duration=execution.duration,
        plan_id=plan_id,
    )


def _auth_context_from_result(
    result: WorkflowExecutionResult,
) -> AuthenticatedExecutionContext | None:
    user_id = _meta_str(result.metadata, "user_id")
    session_id = _meta_str(result.metadata, "session_id")
    request_id = _meta_str(result.metadata, "request_id") or result.instance_id
    if user_id is None or session_id is None:
        return None
    return AuthenticatedExecutionContext.create(
        user_id=user_id,
        workspace_id=WorkspaceId(result.workspace_id),
        session_id=session_id,
        request_id=request_id,
        conversation_id=_meta_str(result.metadata, "conversation_id"),
        correlation_id=_meta_str(result.metadata, "correlation_id") or result.instance_id,
        source="workflow_engine",
    )


def _step_output_refs(mapping: Mapping[str, object]) -> tuple[str, ...]:
    from memovi_automation.domain.value_objects.workflow import extract_variable_references

    return tuple(
        ref for ref in extract_variable_references(dict(mapping)) if ref.startswith("steps.")
    )


def _collect_outputs(
    definition: WorkflowDefinition,
    context: WorkflowContext,
) -> dict[str, object]:
    if definition.expected_outputs:
        outputs: dict[str, object] = {}
        for name in definition.expected_outputs:
            if name in context.variables:
                outputs[name] = context.variables[name]
            elif name in context.step_outputs:
                outputs[name] = context.step_outputs[name]
        return outputs
    # Default: bound variables plus named step outputs
    outputs = dict(context.variables)
    for step_id, output in context.step_outputs.items():
        outputs.setdefault(step_id, output)
    return outputs
