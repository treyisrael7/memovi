"""FastAPI dependencies for connector routes."""

from typing import Annotated, cast

from fastapi import Depends, Request
from memovi_shared import WorkspaceId
from memovi_shared.fastapi import get_default_active_workspace_id
from sqlalchemy.orm import Session as OrmSession

from memovi_connectors.application.services import ConnectorRegistry, ConnectorScheduler
from memovi_connectors.application.services.filesystem_folder_service import FilesystemFolderService
from memovi_connectors.infrastructure.repositories.sqlalchemy_filesystem_folder_repository import (
    SqlAlchemyFilesystemFolderRepository,
)


def get_database_session() -> OrmSession:
    raise RuntimeError("Connectors database session dependency was not configured.")


DatabaseSession = Annotated[OrmSession, Depends(get_database_session)]

get_active_workspace_id = get_default_active_workspace_id

ActiveWorkspaceId = Annotated[WorkspaceId, Depends(get_active_workspace_id)]


def get_connector_registry(request: Request) -> ConnectorRegistry:
    registry = getattr(request.app.state, "connector_registry", None)
    if registry is None:
        raise RuntimeError("Connector registry was not configured.")
    return cast(ConnectorRegistry, registry)


def get_connector_scheduler(request: Request) -> ConnectorScheduler:
    scheduler = getattr(request.app.state, "connector_scheduler", None)
    if scheduler is None:
        raise RuntimeError("Connector scheduler was not configured.")
    return cast(ConnectorScheduler, scheduler)


def get_filesystem_folder_service(
    request: Request,
    session: DatabaseSession,
    scheduler: Annotated[ConnectorScheduler, Depends(get_connector_scheduler)],
) -> FilesystemFolderService:
    return FilesystemFolderService(
        folders=SqlAlchemyFilesystemFolderRepository(session),
        scheduler=scheduler,
    )
