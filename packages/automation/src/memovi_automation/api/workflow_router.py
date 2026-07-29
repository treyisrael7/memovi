"""HTTP routes for Workflow Automation."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from memovi_observability import get_request_context
from memovi_shared import WorkspaceId

from memovi_automation.api.dependencies import (
    get_active_workspace_id,
    get_authenticated_execution_context,
    get_workflow_engine,
)
from memovi_automation.api.workflow_schemas import (
    ExecuteWorkflowRequest,
    WorkflowDefinitionResponse,
    WorkflowExecutionResultResponse,
    WorkflowHistoryEntryResponse,
    WorkflowHistoryListResponse,
    WorkflowListResponse,
    WorkflowStepResponse,
    WorkflowStepResultResponse,
    WorkflowVariableResponse,
)
from memovi_automation.application.services.workflow_engine import WorkflowEngine
from memovi_automation.domain.exceptions import (
    InvalidWorkflowError,
    UnknownWorkflowError,
)
from memovi_automation.domain.value_objects.authenticated_execution_context import (
    AuthenticatedExecutionContext,
)
from memovi_automation.domain.value_objects.workflow import (
    WorkflowDefinition,
    WorkflowExecutionResult,
    WorkflowHistoryEntry,
)

router = APIRouter(prefix="/workflows", tags=["workflows"])


def _definition_response(definition: WorkflowDefinition) -> WorkflowDefinitionResponse:
    return WorkflowDefinitionResponse(
        workflow_id=definition.workflow_id,
        name=definition.name,
        description=definition.description,
        steps=[
            WorkflowStepResponse(
                step_id=step.step_id,
                capability_id=step.capability_id,
                operation=step.operation,
                input_mapping=dict(step.input_mapping),
                output_mapping=dict(step.output_mapping),
                expected_result=step.expected_result,
                description=step.description,
            )
            for step in definition.steps
        ],
        variables=[
            WorkflowVariableResponse(
                name=variable.name,
                type=variable.type,
                description=variable.description,
                required=variable.required,
                default=variable.default,
            )
            for variable in definition.variables
        ],
        required_capabilities=list(definition.required_capabilities),
        expected_outputs=list(definition.expected_outputs),
        metadata=dict(definition.metadata),
    )


def _result_response(result: WorkflowExecutionResult) -> WorkflowExecutionResultResponse:
    return WorkflowExecutionResultResponse(
        instance_id=result.instance_id,
        workflow_id=result.workflow_id,
        workflow_name=result.workflow_name,
        workspace_id=result.workspace_id,
        status=result.status,
        completed_steps=list(result.completed_steps),
        failed_steps=list(result.failed_steps),
        step_results=[
            WorkflowStepResultResponse(
                step_id=step.step_id,
                capability_id=step.capability_id,
                operation=step.operation,
                execution_id=step.execution_id,
                status=step.status,
                output=step.output,
                error_code=step.error_code,
                error_message=step.error_message,
                duration=step.duration,
                plan_id=step.plan_id,
            )
            for step in result.step_results
        ],
        duration=result.duration,
        outputs=dict(result.outputs),
        errors=list(result.errors),
        audit_references=list(result.audit_references),
        started_at=result.started_at,
        finished_at=result.finished_at,
        metadata=dict(result.metadata),
    )


def _history_response(entry: WorkflowHistoryEntry) -> WorkflowHistoryEntryResponse:
    return WorkflowHistoryEntryResponse(
        instance_id=entry.instance_id,
        workflow_id=entry.workflow_id,
        workflow_name=entry.workflow_name,
        workspace_id=entry.workspace_id,
        status=entry.status,
        executed_at=entry.executed_at,
        duration=entry.duration,
        result_summary=dict(entry.result_summary),
        executed_capabilities=list(entry.executed_capabilities),
        audit_references=list(entry.audit_references),
    )


@router.get(
    "",
    response_model=WorkflowListResponse,
    summary="List reusable workflows",
)
def list_workflows(
    engine: Annotated[WorkflowEngine, Depends(get_workflow_engine)],
) -> WorkflowListResponse:
    items = [_definition_response(item) for item in engine.list_workflows()]
    return WorkflowListResponse(items=items, count=len(items))


@router.get(
    "/history",
    response_model=WorkflowHistoryListResponse,
    summary="List workflow execution history",
)
def list_workflow_history(
    engine: Annotated[WorkflowEngine, Depends(get_workflow_engine)],
    workspace_id: Annotated[WorkspaceId, Depends(get_active_workspace_id)],
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> WorkflowHistoryListResponse:
    entries = engine.history.list_for_workspace(workspace_id=workspace_id, limit=limit)
    items = [_history_response(entry) for entry in entries]
    return WorkflowHistoryListResponse(items=items, count=len(items))


@router.get(
    "/history/{instance_id}",
    response_model=WorkflowExecutionResultResponse,
    summary="Get a workflow execution result",
)
def get_workflow_history_result(
    instance_id: str,
    engine: Annotated[WorkflowEngine, Depends(get_workflow_engine)],
    workspace_id: Annotated[WorkspaceId, Depends(get_active_workspace_id)],
) -> WorkflowExecutionResultResponse:
    result = engine.history.get_result(instance_id, workspace_id=workspace_id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow execution '{instance_id}' was not found.",
        )
    return _result_response(result)


@router.get(
    "/{workflow_id}",
    response_model=WorkflowDefinitionResponse,
    summary="Get a workflow definition",
)
def get_workflow(
    workflow_id: str,
    engine: Annotated[WorkflowEngine, Depends(get_workflow_engine)],
) -> WorkflowDefinitionResponse:
    try:
        definition = engine.get_workflow(workflow_id)
    except UnknownWorkflowError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except InvalidWorkflowError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"message": str(exc), "code": exc.code, "details": exc.details},
        ) from exc
    return _definition_response(definition)


@router.post(
    "/{workflow_id}/execute",
    response_model=WorkflowExecutionResultResponse,
    summary="Execute a reusable workflow",
)
def execute_workflow(
    workflow_id: str,
    body: ExecuteWorkflowRequest,
    engine: Annotated[WorkflowEngine, Depends(get_workflow_engine)],
    workspace_id: Annotated[WorkspaceId, Depends(get_active_workspace_id)],
    auth_context: Annotated[
        AuthenticatedExecutionContext,
        Depends(get_authenticated_execution_context),
    ],
) -> WorkflowExecutionResultResponse:
    request_context = get_request_context()
    correlation_id = body.correlation_id
    if correlation_id is None and request_context is not None:
        correlation_id = request_context.correlation_id or request_context.request_id
    try:
        result = engine.execute(
            workflow_id=workflow_id,
            workspace_id=workspace_id,
            auth_context=auth_context,
            variables=body.variables,
            conversation_id=body.conversation_id,
            correlation_id=correlation_id,
        )
    except UnknownWorkflowError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except InvalidWorkflowError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"message": str(exc), "code": exc.code, "details": exc.details},
        ) from exc
    return _result_response(result)
