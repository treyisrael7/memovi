from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from memovi_observability import timed_operation
from memovi_shared import WorkspaceId

from memovi_memory.api.dependencies import (
    get_active_workspace_id,
    get_resource_metadata_service,
)
from memovi_memory.api.tag_schemas import ResourceMetadataResponse, UpsertResourceMetadataRequest
from memovi_memory.application.dto import ResourceMetadataDto
from memovi_memory.application.services import ResourceMetadataService
from memovi_memory.domain.exceptions import (
    InvalidCollectionMembershipError,
    InvalidResourceMetadataError,
    ResourceMetadataNotFoundError,
)

router = APIRouter(prefix="/resource-metadata", tags=["resource-metadata"])


def _metadata_response(dto: ResourceMetadataDto) -> ResourceMetadataResponse:
    return ResourceMetadataResponse(
        workspace_id=dto.workspace_id,
        member_kind=dto.member_kind,
        member_id=dto.member_id,
        title=dto.title,
        description=dto.description,
        notes=dto.notes,
        updated_at=dto.updated_at,
    )


@router.get(
    "/{member_kind}/{member_id}",
    response_model=ResourceMetadataResponse,
    status_code=status.HTTP_200_OK,
    summary="Get resource metadata",
)
def get_resource_metadata(
    member_kind: str,
    member_id: str,
    service: Annotated[ResourceMetadataService, Depends(get_resource_metadata_service)],
    workspace_id: Annotated[WorkspaceId, Depends(get_active_workspace_id)],
) -> ResourceMetadataResponse:
    try:
        with timed_operation(
            "resource_metadata.get",
            attributes={"operation": "resource_metadata.get"},
        ):
            metadata = service.get(
                workspace_id=workspace_id,
                member_kind=member_kind,
                member_id=member_id,
            )
    except ResourceMetadataNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except InvalidCollectionMembershipError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    return _metadata_response(metadata)


@router.put(
    "/{member_kind}/{member_id}",
    response_model=ResourceMetadataResponse,
    status_code=status.HTTP_200_OK,
    summary="Upsert resource metadata",
)
def upsert_resource_metadata(
    member_kind: str,
    member_id: str,
    body: UpsertResourceMetadataRequest,
    service: Annotated[ResourceMetadataService, Depends(get_resource_metadata_service)],
    workspace_id: Annotated[WorkspaceId, Depends(get_active_workspace_id)],
) -> ResourceMetadataResponse:
    try:
        with timed_operation(
            "resource_metadata.upsert",
            attributes={"operation": "resource_metadata.upsert"},
        ):
            metadata = service.upsert(
                workspace_id=workspace_id,
                member_kind=member_kind,
                member_id=member_id,
                title=body.title,
                description=body.description,
                notes=body.notes,
            )
    except (InvalidResourceMetadataError, InvalidCollectionMembershipError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    return _metadata_response(metadata)
