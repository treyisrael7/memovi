"""Shared test helpers for automation package suites."""

from __future__ import annotations

from uuid import uuid4

from memovi_shared import WorkspaceId

from memovi_automation.domain.value_objects.authenticated_execution_context import (
    AuthenticatedExecutionContext,
)


def make_auth_context(
    *,
    workspace_id: WorkspaceId | None = None,
    user_id: str = "test-user",
    session_id: str | None = None,
    request_id: str | None = None,
    source: str = "test",
) -> AuthenticatedExecutionContext:
    """Build an AuthenticatedExecutionContext for unit/acceptance tests."""
    return AuthenticatedExecutionContext.create(
        user_id=user_id,
        workspace_id=workspace_id or WorkspaceId.default(),
        session_id=session_id or f"session-{uuid4()}",
        request_id=request_id or f"request-{uuid4()}",
        source=source,
    )
