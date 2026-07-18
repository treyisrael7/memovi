"""Request-scoped context propagated across services without minting IDs locally."""

from __future__ import annotations

import uuid
from contextvars import ContextVar, Token
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from typing import Any

from memovi_shared import WorkspaceId

_request_context: ContextVar[RequestContext | None] = ContextVar(
    "memovi_request_context",
    default=None,
)


@dataclass(frozen=True, slots=True)
class RequestContext:
    """Stable identifiers and metadata for a single request or worker unit of work."""

    request_id: str
    workspace_id: WorkspaceId | None
    correlation_id: str | None
    timestamp: datetime
    principal: str | None = None

    @classmethod
    def create(
        cls,
        *,
        request_id: str | None = None,
        workspace_id: WorkspaceId | None = None,
        correlation_id: str | None = None,
        timestamp: datetime | None = None,
        principal: str | None = None,
    ) -> RequestContext:
        return cls(
            request_id=request_id or str(uuid.uuid4()),
            workspace_id=workspace_id,
            correlation_id=correlation_id,
            timestamp=timestamp or datetime.now(UTC),
            principal=principal,
        )

    def with_workspace_id(self, workspace_id: WorkspaceId) -> RequestContext:
        return replace(self, workspace_id=workspace_id)

    def as_log_fields(self) -> dict[str, Any]:
        fields: dict[str, Any] = {"request_id": self.request_id}
        if self.workspace_id is not None:
            fields["workspace_id"] = self.workspace_id.value
        if self.correlation_id is not None:
            fields["correlation_id"] = self.correlation_id
        if self.principal is not None:
            fields["principal"] = self.principal
        return fields


def bind_request_context(context: RequestContext) -> Token[RequestContext | None]:
    return _request_context.set(context)


def get_request_context() -> RequestContext | None:
    return _request_context.get()


def clear_request_context(token: Token[RequestContext | None] | None = None) -> None:
    if token is not None:
        _request_context.reset(token)
        return
    _request_context.set(None)


def update_request_context(**changes: Any) -> RequestContext | None:
    """Replace fields on the bound context. Returns the updated context or None."""
    current = get_request_context()
    if current is None:
        return None
    updated = replace(current, **changes)
    _request_context.set(updated)
    return updated
