from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from memovi_shared import InvalidWorkspaceIdError

from memovi_workspace.api.dependencies import (
    get_create_workspace,
    get_list_workspaces_query,
    get_workspace_query,
)
from memovi_workspace.api.schemas import (
    CreateWorkspaceRequest,
    WorkspaceListResponse,
    WorkspaceResponse,
)
from memovi_workspace.application.commands import CreateWorkspace, CreateWorkspaceCommand
from memovi_workspace.application.queries import GetWorkspace, GetWorkspaceQuery, ListWorkspaces
from memovi_workspace.domain.exceptions import WorkspaceDomainError, WorkspaceNotFoundError

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


@router.post(
    "",
    response_model=WorkspaceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a workspace",
)
def create_workspace(
    body: CreateWorkspaceRequest,
    use_case: Annotated[CreateWorkspace, Depends(get_create_workspace)],
) -> WorkspaceResponse:
    try:
        result = use_case.execute(CreateWorkspaceCommand(name=body.name))
    except WorkspaceDomainError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc

    return WorkspaceResponse(
        id=result.workspace.id,
        name=result.workspace.name,
        created_at=result.workspace.created_at,
    )


@router.get(
    "",
    response_model=WorkspaceListResponse,
    status_code=status.HTTP_200_OK,
    summary="List workspaces",
)
def list_workspaces(
    use_case: Annotated[ListWorkspaces, Depends(get_list_workspaces_query)],
) -> WorkspaceListResponse:
    workspaces = use_case.execute()
    return WorkspaceListResponse(
        workspaces=[
            WorkspaceResponse(
                id=workspace.id,
                name=workspace.name,
                created_at=workspace.created_at,
            )
            for workspace in workspaces
        ],
        count=len(workspaces),
    )


@router.get(
    "/{workspace_id}",
    response_model=WorkspaceResponse,
    status_code=status.HTTP_200_OK,
    summary="Get a workspace",
)
def get_workspace(
    workspace_id: str,
    use_case: Annotated[GetWorkspace, Depends(get_workspace_query)],
) -> WorkspaceResponse:
    try:
        workspace = use_case.execute(GetWorkspaceQuery(workspace_id=workspace_id))
    except InvalidWorkspaceIdError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    except WorkspaceNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    return WorkspaceResponse(
        id=workspace.id,
        name=workspace.name,
        created_at=workspace.created_at,
    )
