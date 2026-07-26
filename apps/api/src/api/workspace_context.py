"""Resolve the active WorkspaceId at the API boundary with membership checks."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Annotated

from auth.application.dto import AuthenticatedPrincipal
from fastapi import Depends, Header, HTTPException, Request, status
from memovi_observability import RequestContext, bind_request_context, get_request_context
from memovi_shared import DEFAULT_WORKSPACE_ID, InvalidWorkspaceIdError, WorkspaceId
from memovi_workspace.domain.exceptions import WorkspaceNotFoundError
from memovi_workspace.infrastructure.repositories import (
    SqlAlchemyWorkspaceMembershipRepository,
    SqlAlchemyWorkspaceRepository,
)
from sqlalchemy.orm import Session as OrmSession

from api.auth_context import get_authenticated_principal
from api.database import database_session

WORKSPACE_HEADER = "X-Memovi-Workspace-Id"


@dataclass(slots=True)
class BoundRequestContext:
    """Live view of request-scoped context stored on ``request.state``."""

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
    *,
    principal: AuthenticatedPrincipal | None = None,
) -> WorkspaceId:
    """Keep RequestContext aligned with the resolved active workspace and principal."""
    current = getattr(request.state, "request_context", None) or get_request_context()
    principal_id = None if principal is None else principal.user_id
    if current is None:
        current = RequestContext.create(
            workspace_id=workspace_id,
            principal=principal_id,
        )
    else:
        current = RequestContext(
            request_id=current.request_id,
            workspace_id=workspace_id,
            correlation_id=current.correlation_id,
            timestamp=current.timestamp,
            principal=principal_id or current.principal,
        )
    request.state.request_context = current
    bind_request_context(current)
    return workspace_id


async def get_active_workspace_id(
    request: Request,
    session: Annotated[OrmSession, Depends(database_session)],
    principal: Annotated[AuthenticatedPrincipal, Depends(get_authenticated_principal)],
    x_memovi_workspace_id: Annotated[str | None, Header(alias=WORKSPACE_HEADER)] = None,
) -> WorkspaceId:
    """Resolve the active workspace and validate authenticated membership.

    When the header is omitted, fall back to the seeded Default Workspace.
    Explicit headers must identify an existing workspace the user belongs to.
    """
    if x_memovi_workspace_id is None or not x_memovi_workspace_id.strip():
        workspace_id = DEFAULT_WORKSPACE_ID
    else:
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
            ) from WorkspaceNotFoundError(
                f"Workspace '{workspace_id.value}' was not found.",
            )

    memberships = SqlAlchemyWorkspaceMembershipRepository(session)
    if not memberships.is_member(user_id=principal.user_id, workspace_id=workspace_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Not a member of workspace '{workspace_id.value}'.",
        )

    return _bind_workspace_to_request_context(
        request,
        workspace_id,
        principal=principal,
    )


async def get_request_context_dependency(request: Request) -> BoundRequestContext:
    """Expose the middleware-bound RequestContext to route handlers and services."""
    context = getattr(request.state, "request_context", None)
    if context is not None:
        bind_request_context(context)
    elif get_request_context() is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Request context is not available.",
        )
    return BoundRequestContext(_request=request)
