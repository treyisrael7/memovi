from typing import Annotated

from fastapi import Header, HTTPException, status

from memovi_shared.exceptions import InvalidWorkspaceIdError
from memovi_shared.workspace_header import WORKSPACE_HEADER, parse_workspace_id
from memovi_shared.workspace_id import WorkspaceId


def get_default_active_workspace_id(
    x_memovi_workspace_id: Annotated[str | None, Header(alias=WORKSPACE_HEADER)] = None,
) -> WorkspaceId:
    """Package-default workspace resolution from ``X-Memovi-Workspace-Id``.

    The composition root overrides this with membership-aware resolution in
    ``apps/api`` when serving production traffic.
    """
    try:
        return parse_workspace_id(x_memovi_workspace_id)
    except InvalidWorkspaceIdError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
