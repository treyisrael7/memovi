from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from memovi_observability import DiagnosticEventEmitter, DiagnosticEventName, timed_operation
from memovi_shared import InvalidWorkspaceIdError

from memovi_workspace.api.dependencies import (
    AuthenticatedUserId,
    get_create_workspace,
    get_invite_workspace_member,
    get_leave_workspace,
    get_list_workspace_members,
    get_list_workspaces_query,
    get_remove_workspace_member,
    get_transfer_workspace_ownership,
    get_workspace_query,
)
from memovi_workspace.api.schemas import (
    CreateWorkspaceRequest,
    InviteWorkspaceMemberRequest,
    TransferWorkspaceOwnershipRequest,
    TransferWorkspaceOwnershipResponse,
    WorkspaceListResponse,
    WorkspaceMembershipListResponse,
    WorkspaceMembershipResponse,
    WorkspaceResponse,
)
from memovi_workspace.application.commands import (
    CreateWorkspace,
    CreateWorkspaceCommand,
    InviteWorkspaceMember,
    InviteWorkspaceMemberCommand,
    LeaveWorkspace,
    LeaveWorkspaceCommand,
    RemoveWorkspaceMember,
    RemoveWorkspaceMemberCommand,
    TransferWorkspaceOwnership,
    TransferWorkspaceOwnershipCommand,
)
from memovi_workspace.application.dto import WorkspaceDto, WorkspaceMembershipDto
from memovi_workspace.application.queries import (
    GetWorkspace,
    GetWorkspaceQuery,
    ListWorkspaceMembers,
    ListWorkspaceMembersQuery,
    ListWorkspaces,
    ListWorkspacesQuery,
)
from memovi_workspace.domain.exceptions import (
    CannotLeaveAsSoleOwnerError,
    CannotRemoveLastOwnerError,
    WorkspaceDomainError,
    WorkspaceMemberAlreadyExistsError,
    WorkspaceMemberNotFoundError,
    WorkspaceMembershipRequiredError,
    WorkspaceNotFoundError,
    WorkspaceOwnerRequiredError,
    WorkspaceUserNotFoundError,
)

router = APIRouter(prefix="/workspaces", tags=["workspaces"])
_DIAGNOSTICS = DiagnosticEventEmitter()


def _workspace_response(workspace: WorkspaceDto) -> WorkspaceResponse:
    return WorkspaceResponse(
        id=workspace.id,
        name=workspace.name,
        created_at=workspace.created_at,
        role=workspace.role,
    )


def _membership_response(membership: WorkspaceMembershipDto) -> WorkspaceMembershipResponse:
    return WorkspaceMembershipResponse(
        id=membership.id,
        workspace_id=membership.workspace_id,
        user_id=membership.user_id,
        role=membership.role,
        created_at=membership.created_at,
        email=membership.email,
    )


def _map_membership_error(exc: WorkspaceDomainError) -> HTTPException:
    if isinstance(exc, WorkspaceNotFoundError | WorkspaceMemberNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    if isinstance(
        exc,
        WorkspaceMembershipRequiredError
        | WorkspaceOwnerRequiredError
        | CannotRemoveLastOwnerError
        | CannotLeaveAsSoleOwnerError,
    ):
        return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    if isinstance(exc, WorkspaceMemberAlreadyExistsError):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    if isinstance(exc, WorkspaceUserNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        detail=str(exc),
    )


@router.post(
    "",
    response_model=WorkspaceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a workspace",
)
def create_workspace(
    body: CreateWorkspaceRequest,
    use_case: Annotated[CreateWorkspace, Depends(get_create_workspace)],
    user_id: AuthenticatedUserId,
) -> WorkspaceResponse:
    try:
        with timed_operation("workspace.create", attributes={"operation": "workspace.create"}):
            result = use_case.execute(
                CreateWorkspaceCommand(name=body.name, owner_user_id=user_id),
            )
    except WorkspaceDomainError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc

    _DIAGNOSTICS.emit(
        DiagnosticEventName.WORKSPACE_CREATED,
        workspace_id=result.workspace.id,
        workspace_name=result.workspace.name,
    )
    return WorkspaceResponse(
        id=result.workspace.id,
        name=result.workspace.name,
        created_at=result.workspace.created_at,
        role="owner",
    )


@router.get(
    "",
    response_model=WorkspaceListResponse,
    status_code=status.HTTP_200_OK,
    summary="List workspaces",
)
def list_workspaces(
    use_case: Annotated[ListWorkspaces, Depends(get_list_workspaces_query)],
    user_id: AuthenticatedUserId,
) -> WorkspaceListResponse:
    workspaces = use_case.execute(ListWorkspacesQuery(user_id=user_id))
    return WorkspaceListResponse(
        workspaces=[_workspace_response(workspace) for workspace in workspaces],
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
    user_id: AuthenticatedUserId,
) -> WorkspaceResponse:
    try:
        workspace = use_case.execute(
            GetWorkspaceQuery(workspace_id=workspace_id, user_id=user_id),
        )
    except InvalidWorkspaceIdError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    except WorkspaceMembershipRequiredError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
    except WorkspaceNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    return _workspace_response(workspace)


@router.get(
    "/{workspace_id}/members",
    response_model=WorkspaceMembershipListResponse,
    status_code=status.HTTP_200_OK,
    summary="List workspace members",
)
def list_workspace_members(
    workspace_id: str,
    use_case: Annotated[ListWorkspaceMembers, Depends(get_list_workspace_members)],
    user_id: AuthenticatedUserId,
) -> WorkspaceMembershipListResponse:
    try:
        members = use_case.execute(
            ListWorkspaceMembersQuery(workspace_id=workspace_id, actor_user_id=user_id),
        )
    except InvalidWorkspaceIdError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    except WorkspaceDomainError as exc:
        raise _map_membership_error(exc) from exc
    return WorkspaceMembershipListResponse(
        items=[_membership_response(item) for item in members],
        count=len(members),
    )


@router.post(
    "/{workspace_id}/members",
    response_model=WorkspaceMembershipResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Invite a registered user to the workspace",
)
def invite_workspace_member(
    workspace_id: str,
    body: InviteWorkspaceMemberRequest,
    use_case: Annotated[InviteWorkspaceMember, Depends(get_invite_workspace_member)],
    user_id: AuthenticatedUserId,
) -> WorkspaceMembershipResponse:
    try:
        membership = use_case.execute(
            InviteWorkspaceMemberCommand(
                workspace_id=workspace_id,
                actor_user_id=user_id,
                email=str(body.email),
            )
        )
    except InvalidWorkspaceIdError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    except WorkspaceDomainError as exc:
        raise _map_membership_error(exc) from exc
    return _membership_response(membership)


@router.delete(
    "/{workspace_id}/members/{member_user_id}",
    response_model=WorkspaceMembershipResponse,
    status_code=status.HTTP_200_OK,
    summary="Remove a workspace member",
)
def remove_workspace_member(
    workspace_id: str,
    member_user_id: str,
    use_case: Annotated[RemoveWorkspaceMember, Depends(get_remove_workspace_member)],
    user_id: AuthenticatedUserId,
) -> WorkspaceMembershipResponse:
    try:
        membership = use_case.execute(
            RemoveWorkspaceMemberCommand(
                workspace_id=workspace_id,
                actor_user_id=user_id,
                target_user_id=member_user_id,
            )
        )
    except InvalidWorkspaceIdError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    except WorkspaceDomainError as exc:
        raise _map_membership_error(exc) from exc
    return _membership_response(membership)


@router.post(
    "/{workspace_id}/transfer-ownership",
    response_model=TransferWorkspaceOwnershipResponse,
    status_code=status.HTTP_200_OK,
    summary="Transfer workspace ownership",
)
def transfer_workspace_ownership(
    workspace_id: str,
    body: TransferWorkspaceOwnershipRequest,
    use_case: Annotated[
        TransferWorkspaceOwnership,
        Depends(get_transfer_workspace_ownership),
    ],
    user_id: AuthenticatedUserId,
) -> TransferWorkspaceOwnershipResponse:
    try:
        result = use_case.execute(
            TransferWorkspaceOwnershipCommand(
                workspace_id=workspace_id,
                actor_user_id=user_id,
                new_owner_user_id=body.new_owner_user_id,
            )
        )
    except InvalidWorkspaceIdError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    except WorkspaceDomainError as exc:
        raise _map_membership_error(exc) from exc
    return TransferWorkspaceOwnershipResponse(
        previous_owner=_membership_response(result.previous_owner),
        new_owner=_membership_response(result.new_owner),
    )


@router.post(
    "/{workspace_id}/leave",
    response_model=WorkspaceMembershipResponse,
    status_code=status.HTTP_200_OK,
    summary="Leave a workspace",
)
def leave_workspace(
    workspace_id: str,
    use_case: Annotated[LeaveWorkspace, Depends(get_leave_workspace)],
    user_id: AuthenticatedUserId,
) -> WorkspaceMembershipResponse:
    try:
        membership = use_case.execute(
            LeaveWorkspaceCommand(workspace_id=workspace_id, user_id=user_id),
        )
    except InvalidWorkspaceIdError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    except WorkspaceDomainError as exc:
        raise _map_membership_error(exc) from exc
    return _membership_response(membership)
