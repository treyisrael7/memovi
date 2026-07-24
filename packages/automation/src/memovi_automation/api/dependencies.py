from typing import Annotated, cast

from fastapi import Header, HTTPException, Request, status
from memovi_shared import DEFAULT_WORKSPACE_ID, InvalidWorkspaceIdError, WorkspaceId

from memovi_automation.application.services.capability_execution_engine import (
    CapabilityExecutionEngine,
)

WORKSPACE_HEADER = "X-Memovi-Workspace-Id"


def get_active_workspace_id(
    x_memovi_workspace_id: Annotated[str | None, Header(alias=WORKSPACE_HEADER)] = None,
) -> WorkspaceId:
    if x_memovi_workspace_id is None or not x_memovi_workspace_id.strip():
        return DEFAULT_WORKSPACE_ID
    try:
        return WorkspaceId(x_memovi_workspace_id.strip())
    except InvalidWorkspaceIdError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc


def get_capability_execution_engine(request: Request) -> CapabilityExecutionEngine:
    engine = getattr(request.app.state, "capability_execution_engine", None)
    if engine is None:
        raise RuntimeError("Capability execution engine was not configured.")
    return cast(CapabilityExecutionEngine, engine)
