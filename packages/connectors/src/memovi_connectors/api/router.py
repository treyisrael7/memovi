"""HTTP routes for the Connector Framework and Filesystem Connector."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from memovi_shared import WorkspaceId

from memovi_connectors.api.dependencies import (
    get_active_workspace_id,
    get_connector_registry,
    get_filesystem_folder_service,
)
from memovi_connectors.api.schemas import (
    AddFilesystemFolderRequest,
    ConnectorHealthListResponse,
    ConnectorHealthResponse,
    ConnectorListResponse,
    ConnectorMetadataResponse,
    FilesystemFolderListResponse,
    FilesystemFolderResponse,
    SyncFilesystemFolderRequest,
    SyncFilesystemFolderResponse,
)
from memovi_connectors.application.services import ConnectorRegistry
from memovi_connectors.application.services.filesystem_folder_service import (
    AddFilesystemFolderCommand,
    FilesystemFolderService,
    SyncFilesystemFolderCommand,
)
from memovi_connectors.domain.entities import FilesystemFolderConnection
from memovi_connectors.domain.exceptions import (
    InvalidConnectorError,
    UnknownConnectorError,
)

router = APIRouter(prefix="/connectors", tags=["connectors"])


def _folder_response(folder: FilesystemFolderConnection) -> FilesystemFolderResponse:
    return FilesystemFolderResponse(
        id=folder.id,
        workspace_id=folder.workspace_id.value,
        root_path=folder.root_path,
        display_name=folder.display_name,
        sync_status=folder.sync_status,
        last_error=folder.last_error,
        imported_document_count=folder.imported_document_count,
        last_synchronized_at=folder.last_synchronized_at,
        created_at=folder.created_at,  # type: ignore[arg-type]
        updated_at=folder.updated_at,  # type: ignore[arg-type]
    )


@router.get(
    "",
    response_model=ConnectorListResponse,
    status_code=status.HTTP_200_OK,
    summary="List registered connectors",
)
def list_connectors(
    registry: Annotated[ConnectorRegistry, Depends(get_connector_registry)],
) -> ConnectorListResponse:
    items = [
        ConnectorMetadataResponse(
            connector_id=meta.connector_id,
            display_name=meta.display_name,
            description=meta.description,
            source_category=meta.source_category,
            auth_methods=list(meta.auth_methods),
            supports_incremental_sync=meta.supports_incremental_sync,
            supports_delete_detection=meta.supports_delete_detection,
        )
        for meta in registry.list_metadata()
    ]
    return ConnectorListResponse(items=items, count=len(items))


@router.get(
    "/health",
    response_model=ConnectorHealthListResponse,
    status_code=status.HTTP_200_OK,
    summary="Connector health snapshots",
)
def list_connector_health(
    registry: Annotated[ConnectorRegistry, Depends(get_connector_registry)],
) -> ConnectorHealthListResponse:
    items = [
        ConnectorHealthResponse(
            connector_id=health.connector_id,
            status=health.status,
            last_synchronized_at=health.last_synchronized_at,
            imported_document_count=health.imported_document_count,
            pending_changes=health.pending_changes,
            errors=list(health.errors),
            message=health.message,
        )
        for health in registry.health_all()
    ]
    return ConnectorHealthListResponse(items=items, count=len(items))


@router.get(
    "/filesystem/folders",
    response_model=FilesystemFolderListResponse,
    status_code=status.HTTP_200_OK,
    summary="List connected filesystem folders",
)
def list_filesystem_folders(
    service: Annotated[FilesystemFolderService, Depends(get_filesystem_folder_service)],
    workspace_id: Annotated[WorkspaceId, Depends(get_active_workspace_id)],
) -> FilesystemFolderListResponse:
    folders = service.list_folders(workspace_id=workspace_id)
    return FilesystemFolderListResponse(
        items=[_folder_response(folder) for folder in folders],
        count=len(folders),
    )


@router.post(
    "/filesystem/folders",
    response_model=FilesystemFolderResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Connect a local folder",
)
def add_filesystem_folder(
    body: AddFilesystemFolderRequest,
    service: Annotated[FilesystemFolderService, Depends(get_filesystem_folder_service)],
    workspace_id: Annotated[WorkspaceId, Depends(get_active_workspace_id)],
) -> FilesystemFolderResponse:
    try:
        folder = service.add_folder(
            AddFilesystemFolderCommand(
                workspace_id=workspace_id,
                root_path=body.root_path,
                display_name=body.display_name,
            ),
        )
    except InvalidConnectorError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    return _folder_response(folder)


@router.delete(
    "/filesystem/folders/{folder_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove a connected folder",
)
def remove_filesystem_folder(
    folder_id: str,
    service: Annotated[FilesystemFolderService, Depends(get_filesystem_folder_service)],
    workspace_id: Annotated[WorkspaceId, Depends(get_active_workspace_id)],
) -> None:
    try:
        service.remove_folder(workspace_id=workspace_id, folder_id=folder_id)
    except UnknownConnectorError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.post(
    "/filesystem/folders/{folder_id}/sync",
    response_model=SyncFilesystemFolderResponse,
    status_code=status.HTTP_200_OK,
    summary="Manually synchronize a connected folder",
)
def sync_filesystem_folder(
    folder_id: str,
    service: Annotated[FilesystemFolderService, Depends(get_filesystem_folder_service)],
    workspace_id: Annotated[WorkspaceId, Depends(get_active_workspace_id)],
    body: SyncFilesystemFolderRequest | None = None,
) -> SyncFilesystemFolderResponse:
    sync_mode = body.sync_mode if body is not None else None
    try:
        result = service.sync_folder(
            SyncFilesystemFolderCommand(
                workspace_id=workspace_id,
                folder_id=folder_id,
                sync_mode=sync_mode,
            ),
        )
    except UnknownConnectorError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except InvalidConnectorError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    folder = service.get_folder(workspace_id=workspace_id, folder_id=folder_id)
    if folder is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Filesystem folder '{folder_id}' was not found after sync.",
        )

    return SyncFilesystemFolderResponse(
        folder=_folder_response(folder),
        success=result.success,
        sync_mode=result.sync_mode,
        imported_count=result.imported_count,
        updated_count=result.updated_count,
        deleted_count=result.deleted_count,
        skipped_count=result.skipped_count,
        error_code=result.error_code,
        error_message=result.error_message,
    )
