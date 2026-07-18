from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session as OrmSession

from memovi_workspace.application.commands import CreateWorkspace
from memovi_workspace.application.queries import GetWorkspace, ListWorkspaces
from memovi_workspace.infrastructure.repositories import SqlAlchemyWorkspaceRepository


def get_database_session() -> OrmSession:
    raise RuntimeError("Workspace database session dependency was not configured.")


DatabaseSession = Annotated[OrmSession, Depends(get_database_session)]


def get_create_workspace(session: DatabaseSession) -> CreateWorkspace:
    return CreateWorkspace(workspaces=SqlAlchemyWorkspaceRepository(session))


def get_workspace_query(session: DatabaseSession) -> GetWorkspace:
    return GetWorkspace(workspaces=SqlAlchemyWorkspaceRepository(session))


def get_list_workspaces_query(session: DatabaseSession) -> ListWorkspaces:
    return ListWorkspaces(workspaces=SqlAlchemyWorkspaceRepository(session))
