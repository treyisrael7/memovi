"""Resolve the active WorkspaceId at the API boundary."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request, status
from memovi_observability import RequestContext, bind_request_context, get_request_context
from memovi_shared import DEFAULT_WORKSPACE_ID, InvalidWorkspaceIdError, WorkspaceId
from memovi_workspace.domain.exceptions import WorkspaceNotFoundError
from memovi_workspace.infrastructure.repositories import SqlAlchemyWorkspaceRepository
from sqlalchemy.orm import Session as OrmSession

from api.database import database_session

WORKSPACE_HEADER = "X-Memovi-Workspace-Id"


@dataclass(slots=True)
class BoundRequestContext:
    """Live view of request-scoped context stored on ``request.state``.

    FastAPI caches dependency results, so returning a snapshot can miss later
    workspace binding. This proxy always reads the current request context.
    """

    _request: Request

    def _current(self) -> RequestContext:
        context = getattr(self._request.state, "request_context", None) or get_request_context()
        if context is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Request context is not available.",
            )
        return context

    @property
    def request_id(self) -> str:
        return self._current().request_id

    @property
    def workspace_id(self) -> WorkspaceId | None:
        return self._current().workspace_id

    @property
    def correlation_id(self) -> str | None:
        return self._current().correlation_id

    @property
    def timestamp(self) -> datetime:
        return self._current().timestamp

    @property
    def principal(self) -> str | None:
        return self._current().principal

    def as_log_fields(self) -> dict[str, object]:
        return self._current().as_log_fields()


def _bind_workspace_to_request_context(
    request: Request,
    workspace_id: WorkspaceId,
) -> WorkspaceId:
    """Keep RequestContext.workspace_id aligned with the resolved active workspace."""
    current = getattr(request.state, "request_context", None) or get_request_context()
    if current is None:
        current = RequestContext.create(workspace_id=workspace_id)
    else:
        current = current.with_workspace_id(workspace_id)
    request.state.request_context = current
    bind_request_context(current)
    return workspace_id


async def get_active_workspace_id(
    request: Request,
    session: Annotated[OrmSession, Depends(database_session)],
    x_memovi_workspace_id: Annotated[str | None, Header(alias=WORKSPACE_HEADER)] = None,
) -> WorkspaceId:
    """Resolve the active workspace for ownership-sensitive requests.

    When the header is omitted, fall back to the seeded Default Workspace for V1
    backwards compatibility. Explicit headers must identify an existing workspace.

    Implemented as ``async`` so RequestContext binding runs on the event-loop
    context before sync endpoints are dispatched to a threadpool. That keeps
    ``workspace_id`` visible to structured logs for the whole request.
    """
    if x_memovi_workspace_id is None or not x_memovi_workspace_id.strip():
        return _bind_workspace_to_request_context(request, DEFAULT_WORKSPACE_ID)

    try:
        workspace_id = WorkspaceId(x_memovi_workspace_id.strip())
    except InvalidWorkspaceIdError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc

    workspace = SqlAlchemyWorkspaceRepository(session).get_by_id(workspace_id)
    if workspace is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workspace '{workspace_id.value}' was not found.",
        ) from WorkspaceNotFoundError(f"Workspace '{workspace_id.value}' was not found.")

    return _bind_workspace_to_request_context(request, workspace.id)


async def get_request_context_dependency(request: Request) -> BoundRequestContext:
    """Expose the middleware-bound RequestContext to route handlers and services."""
    context = getattr(request.state, "request_context", None)
    if context is not None:
        # Re-bind on the event-loop context so sync handlers inherit workspace_id.
        bind_request_context(context)
    elif get_request_context() is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Request context is not available.",
        )
    return BoundRequestContext(_request=request)
