"""Shared cross-cutting primitives for the Memovi platform."""

from memovi_shared.exceptions import InvalidWorkspaceIdError
from memovi_shared.workspace_id import DEFAULT_WORKSPACE_ID, WorkspaceId

__all__ = [
    "DEFAULT_WORKSPACE_ID",
    "InvalidWorkspaceIdError",
    "WorkspaceId",
]
