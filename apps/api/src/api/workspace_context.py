"""Resolve the active WorkspaceId at the API boundary."""

from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from memovi_shared import DEFAULT_WORKSPACE_ID, InvalidWorkspaceIdError, WorkspaceId
from memovi_workspace.domain.exceptions import WorkspaceNotFoundError
from memovi_workspace.infrastructure.repositories import SqlAlchemyWorkspaceRepository
from sqlalchemy.orm import Session as OrmSession

from api.database import database_session

WORKSPACE_HEADER = "X-Memovi-Workspace-Id"


def get_active_workspace_id(
    session: Annotated[OrmSession, Depends(database_session)],
    x_memovi_workspace_id: Annotated[str | None, Header(alias=WORKSPACE_HEADER)] = None,
) -> WorkspaceId:
    """Resolve the active workspace for ownership-sensitive requests.

    When the header is omitted, fall back to the seeded Default Workspace for V1
    backwards compatibility. Explicit headers must identify an existing workspace.
    """
    if x_memovi_workspace_id is None or not x_memovi_workspace_id.strip():
        return DEFAULT_WORKSPACE_ID

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

    return workspace.id
