"""Authenticated principal resolution helpers for the API composition root."""

from __future__ import annotations

from typing import Annotated
from uuid import uuid4

from auth.api.dependencies import require_authenticated_principal
from auth.application.dto import AuthenticatedPrincipal
from fastapi import Depends, Request
from memovi_automation.domain.value_objects.authenticated_execution_context import (
    AuthenticatedExecutionContext,
)
from memovi_observability import RequestContext, bind_request_context, get_request_context
from memovi_shared import WorkspaceId


def bind_principal_to_request_context(
    request: Request,
    principal: AuthenticatedPrincipal,
) -> AuthenticatedPrincipal:
    """Attach the authenticated principal to RequestContext for observability."""
    current = getattr(request.state, "request_context", None) or get_request_context()
    if current is None:
        current = RequestContext.create(principal=principal.user_id)
    else:
        current = RequestContext(
            request_id=current.request_id,
            workspace_id=current.workspace_id,
            correlation_id=current.correlation_id,
            timestamp=current.timestamp,
            principal=principal.user_id,
        )
    request.state.request_context = current
    request.state.authenticated_principal = principal
    bind_request_context(current)
    return principal


async def get_authenticated_principal(
    request: Request,
    principal: Annotated[AuthenticatedPrincipal, Depends(require_authenticated_principal)],
) -> AuthenticatedPrincipal:
    return bind_principal_to_request_context(request, principal)


def build_authenticated_execution_context(
    *,
    principal: AuthenticatedPrincipal,
    workspace_id: WorkspaceId,
    request: Request,
    source: str = "api",
    conversation_id: str | None = None,
    correlation_id: str | None = None,
) -> AuthenticatedExecutionContext:
    """Build AuthenticatedExecutionContext from the resolved principal and workspace."""
    request_context = getattr(request.state, "request_context", None) or get_request_context()
    request_id = request_context.request_id if request_context is not None else str(uuid4())
    resolved_correlation = correlation_id
    if resolved_correlation is None and request_context is not None:
        resolved_correlation = request_context.correlation_id
    return AuthenticatedExecutionContext.create(
        user_id=principal.user_id,
        workspace_id=workspace_id,
        session_id=principal.session_id,
        request_id=request_id,
        conversation_id=conversation_id,
        correlation_id=resolved_correlation,
        source=source,
    )
