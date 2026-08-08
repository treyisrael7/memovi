from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session as OrmSession

from memovi_workspace.application.commands import (
    CreateWorkspace,
    InviteWorkspaceMember,
    LeaveWorkspace,
    RemoveWorkspaceMember,
    TransferWorkspaceOwnership,
)
from memovi_workspace.application.ports import UserDirectoryPort
from memovi_workspace.application.queries import (
    GetWorkspace,
    ListWorkspaceMembers,
    ListWorkspaces,
)
from memovi_workspace.infrastructure.repositories import (
    SqlAlchemyWorkspaceMembershipEventRepository,
    SqlAlchemyWorkspaceMembershipRepository,
    SqlAlchemyWorkspaceRepository,
)


def get_database_session() -> OrmSession:
    raise RuntimeError("Workspace database session dependency was not configured.")


def get_authenticated_user_id() -> str:
    raise RuntimeError("Authenticated user dependency was not configured.")


def get_user_directory() -> UserDirectoryPort:
    raise RuntimeError("Workspace user directory dependency was not configured.")


DatabaseSession = Annotated[OrmSession, Depends(get_database_session)]
AuthenticatedUserId = Annotated[str, Depends(get_authenticated_user_id)]
UserDirectory = Annotated[UserDirectoryPort, Depends(get_user_directory)]


def get_create_workspace(session: DatabaseSession) -> CreateWorkspace:
    return CreateWorkspace(
        workspaces=SqlAlchemyWorkspaceRepository(session),
        memberships=SqlAlchemyWorkspaceMembershipRepository(session),
    )


def get_workspace_query(session: DatabaseSession) -> GetWorkspace:
    return GetWorkspace(
        workspaces=SqlAlchemyWorkspaceRepository(session),
        memberships=SqlAlchemyWorkspaceMembershipRepository(session),
    )


def get_list_workspaces_query(session: DatabaseSession) -> ListWorkspaces:
    return ListWorkspaces(
        workspaces=SqlAlchemyWorkspaceRepository(session),
        memberships=SqlAlchemyWorkspaceMembershipRepository(session),
    )


def get_list_workspace_members(
    session: DatabaseSession,
    users: UserDirectory,
) -> ListWorkspaceMembers:
    return ListWorkspaceMembers(
        workspaces=SqlAlchemyWorkspaceRepository(session),
        memberships=SqlAlchemyWorkspaceMembershipRepository(session),
        users=users,
    )


def get_invite_workspace_member(
    session: DatabaseSession,
    users: UserDirectory,
) -> InviteWorkspaceMember:
    return InviteWorkspaceMember(
        workspaces=SqlAlchemyWorkspaceRepository(session),
        memberships=SqlAlchemyWorkspaceMembershipRepository(session),
        events=SqlAlchemyWorkspaceMembershipEventRepository(session),
        users=users,
    )


def get_remove_workspace_member(
    session: DatabaseSession,
    users: UserDirectory,
) -> RemoveWorkspaceMember:
    return RemoveWorkspaceMember(
        workspaces=SqlAlchemyWorkspaceRepository(session),
        memberships=SqlAlchemyWorkspaceMembershipRepository(session),
        events=SqlAlchemyWorkspaceMembershipEventRepository(session),
        users=users,
    )


def get_transfer_workspace_ownership(
    session: DatabaseSession,
    users: UserDirectory,
) -> TransferWorkspaceOwnership:
    return TransferWorkspaceOwnership(
        workspaces=SqlAlchemyWorkspaceRepository(session),
        memberships=SqlAlchemyWorkspaceMembershipRepository(session),
        events=SqlAlchemyWorkspaceMembershipEventRepository(session),
        users=users,
    )


def get_leave_workspace(
    session: DatabaseSession,
    users: UserDirectory,
) -> LeaveWorkspace:
    return LeaveWorkspace(
        workspaces=SqlAlchemyWorkspaceRepository(session),
        memberships=SqlAlchemyWorkspaceMembershipRepository(session),
        events=SqlAlchemyWorkspaceMembershipEventRepository(session),
        users=users,
    )
