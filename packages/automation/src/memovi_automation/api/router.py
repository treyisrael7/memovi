from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from memovi_shared import WorkspaceId

from memovi_automation.api.dependencies import (
    get_active_workspace_id,
    get_capability_execution_engine,
)
from memovi_automation.api.schemas import (
    CapabilityErrorResponse,
    CapabilityExecutionListResponse,
    CapabilityExecutionResponse,
    CapabilityListResponse,
    CapabilityMetadataResponse,
    CapabilityParameterResponse,
    ExecutionAuditEntryResponse,
    ExecutionAuditListResponse,
    PermissionModeResponse,
    SetPermissionModeRequest,
    SubmitCapabilityExecutionRequest,
)
from memovi_automation.application.services.capability_execution_engine import (
    CapabilityExecutionEngine,
)
from memovi_automation.domain.exceptions import (
    CapabilityExecutionNotFoundError,
    InvalidCapabilityArgumentsError,
    UnknownCapabilityError,
)
from memovi_automation.domain.value_objects import (
    CapabilityExecutionPolicy,
    CapabilityExecutionRequest,
    CapabilityExecutionResult,
    CapabilityExecutionStatus,
    PermissionMode,
)

router = APIRouter(prefix="/capabilities", tags=["capabilities"])


def _execution_response(result: CapabilityExecutionResult) -> CapabilityExecutionResponse:
    error = None
    if result.error is not None:
        error = CapabilityErrorResponse(
            code=result.error.code,
            message=result.error.message,
            details=dict(result.error.details),
        )
    return CapabilityExecutionResponse(
        execution_id=result.execution_id,
        capability_id=result.capability_id,
        workspace_id=result.workspace_id,
        status=result.status.value,
        permission_mode=result.permission_mode.value,
        output=result.output,
        error=error,
        duration=result.duration,
        conversation_id=result.conversation_id,
        correlation_id=result.correlation_id,
        created_at=result.created_at,
        updated_at=result.updated_at,
        metadata=dict(result.metadata),
    )


@router.get(
    "",
    response_model=CapabilityListResponse,
    summary="List registered capabilities",
)
def list_capabilities(
    engine: Annotated[CapabilityExecutionEngine, Depends(get_capability_execution_engine)],
    workspace_id: Annotated[WorkspaceId, Depends(get_active_workspace_id)],
) -> CapabilityListResponse:
    items: list[CapabilityMetadataResponse] = []
    for metadata in engine.registry.list():
        mode = engine.get_permission_mode(metadata.id, workspace_id=workspace_id)
        items.append(
            CapabilityMetadataResponse(
                id=metadata.id,
                description=metadata.description,
                permissions=list(metadata.permission_names()),
                parameters=[
                    CapabilityParameterResponse(
                        name=parameter.name,
                        type=parameter.type,
                        description=parameter.description,
                        required=parameter.required,
                    )
                    for parameter in metadata.parameters
                ],
                permission_mode=mode.value,
            )
        )
    return CapabilityListResponse(items=items, count=len(items))


@router.put(
    "/{capability_id}/permission-mode",
    response_model=PermissionModeResponse,
    summary="Set capability permission mode",
)
def set_permission_mode(
    capability_id: str,
    body: SetPermissionModeRequest,
    engine: Annotated[CapabilityExecutionEngine, Depends(get_capability_execution_engine)],
    workspace_id: Annotated[WorkspaceId, Depends(get_active_workspace_id)],
) -> PermissionModeResponse:
    try:
        engine.set_permission_mode(
            capability_id,
            PermissionMode(body.permission_mode),
            workspace_id=workspace_id,
        )
    except UnknownCapabilityError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return PermissionModeResponse(
        capability_id=capability_id,
        permission_mode=body.permission_mode,
    )


@router.post(
    "/executions",
    response_model=CapabilityExecutionResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Submit a capability execution",
    description=(
        "Submit an execution request to the Capability Execution Engine. "
        "Depending on permission mode, the result may be pending_approval, "
        "completed, failed, or cancelled. Intelligence and clients must use "
        "this pipeline rather than invoking capabilities directly."
    ),
)
def submit_execution(
    body: SubmitCapabilityExecutionRequest,
    engine: Annotated[CapabilityExecutionEngine, Depends(get_capability_execution_engine)],
    workspace_id: Annotated[WorkspaceId, Depends(get_active_workspace_id)],
) -> CapabilityExecutionResponse:
    policy = None
    if body.permission_mode is not None or body.timeout_seconds is not None:
        policy = CapabilityExecutionPolicy(
            timeout_seconds=body.timeout_seconds if body.timeout_seconds is not None else 30.0,
            permission_mode=(
                PermissionMode(body.permission_mode) if body.permission_mode is not None else None
            ),
        )
    request = CapabilityExecutionRequest.create(
        capability_id=body.capability_id,
        workspace_id=workspace_id,
        arguments=body.arguments,
        conversation_id=body.conversation_id,
        correlation_id=body.correlation_id,
        policy=policy,
        source="api",
    )
    try:
        result = engine.submit(request)
    except InvalidCapabilityArgumentsError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    return _execution_response(result)


@router.get(
    "/executions",
    response_model=CapabilityExecutionListResponse,
    summary="List capability executions",
)
def list_executions(
    engine: Annotated[CapabilityExecutionEngine, Depends(get_capability_execution_engine)],
    workspace_id: Annotated[WorkspaceId, Depends(get_active_workspace_id)],
    status_filter: Annotated[
        str | None,
        Query(alias="status", description="Filter by execution status."),
    ] = None,
    conversation_id: Annotated[str | None, Query()] = None,
) -> CapabilityExecutionListResponse:
    parsed_status = None
    if status_filter is not None:
        try:
            parsed_status = CapabilityExecutionStatus(status_filter)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"Invalid status '{status_filter}'.",
            ) from exc
    items = engine.list_executions(
        workspace_id=workspace_id,
        status=parsed_status,
        conversation_id=conversation_id,
    )
    return CapabilityExecutionListResponse(
        items=[_execution_response(item) for item in items],
        count=len(items),
    )


@router.get(
    "/executions/audit",
    response_model=ExecutionAuditListResponse,
    summary="List capability execution audit entries",
)
def list_audit(
    engine: Annotated[CapabilityExecutionEngine, Depends(get_capability_execution_engine)],
    workspace_id: Annotated[WorkspaceId, Depends(get_active_workspace_id)],
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> ExecutionAuditListResponse:
    entries = engine.list_audit(workspace_id=workspace_id, limit=limit)
    return ExecutionAuditListResponse(
        items=[
            ExecutionAuditEntryResponse(
                id=entry.id,
                execution_id=entry.execution_id,
                workspace_id=entry.workspace_id,
                capability_id=entry.capability_id,
                status=entry.status.value,
                permission_mode=entry.permission_mode.value,
                arguments=dict(entry.arguments),
                result_summary=dict(entry.result_summary),
                duration=entry.duration,
                timestamp=entry.timestamp,
                conversation_id=entry.conversation_id,
                correlation_id=entry.correlation_id,
                source=entry.source,
            )
            for entry in entries
        ],
        count=len(entries),
    )


@router.get(
    "/executions/{execution_id}",
    response_model=CapabilityExecutionResponse,
    summary="Get capability execution",
)
def get_execution(
    execution_id: str,
    engine: Annotated[CapabilityExecutionEngine, Depends(get_capability_execution_engine)],
    workspace_id: Annotated[WorkspaceId, Depends(get_active_workspace_id)],
) -> CapabilityExecutionResponse:
    try:
        result = engine.get(execution_id, workspace_id=workspace_id)
    except CapabilityExecutionNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return _execution_response(result)


@router.post(
    "/executions/{execution_id}/approve",
    response_model=CapabilityExecutionResponse,
    summary="Approve a pending capability execution",
)
def approve_execution(
    execution_id: str,
    engine: Annotated[CapabilityExecutionEngine, Depends(get_capability_execution_engine)],
    workspace_id: Annotated[WorkspaceId, Depends(get_active_workspace_id)],
) -> CapabilityExecutionResponse:
    try:
        result = engine.approve(execution_id, workspace_id=workspace_id)
    except CapabilityExecutionNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except InvalidCapabilityArgumentsError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    return _execution_response(result)


@router.post(
    "/executions/{execution_id}/cancel",
    response_model=CapabilityExecutionResponse,
    summary="Cancel a capability execution",
)
def cancel_execution(
    execution_id: str,
    engine: Annotated[CapabilityExecutionEngine, Depends(get_capability_execution_engine)],
    workspace_id: Annotated[WorkspaceId, Depends(get_active_workspace_id)],
) -> CapabilityExecutionResponse:
    try:
        result = engine.cancel(execution_id, workspace_id=workspace_id)
    except CapabilityExecutionNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return _execution_response(result)
