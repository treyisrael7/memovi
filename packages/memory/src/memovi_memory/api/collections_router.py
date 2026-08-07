from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from memovi_observability import timed_operation
from memovi_shared import WorkspaceId

from memovi_memory.api.collection_schemas import (
    AddCollectionMemberRequest,
    CollectionListItemResponse,
    CollectionListResponse,
    CollectionMembershipListResponse,
    CollectionMembershipResponse,
    CollectionResponse,
    CollectionActivityResponse,
    CollectionSummaryResponse,
    CreateCollectionRequest,
    RenameCollectionRequest,
    UpdateCollectionDescriptionRequest,
)
from memovi_memory.api.dependencies import get_active_workspace_id, get_collection_service
from memovi_memory.application.services import CollectionService
from memovi_memory.domain.exceptions import (
    CollectionMembershipNotFoundError,
    CollectionNotFoundError,
    DuplicateCollectionMembershipError,
    InvalidCollectionError,
    InvalidCollectionMembershipError,
    MemoryDomainError,
)

router = APIRouter(prefix="/collections", tags=["collections"])


def _collection_response(dto) -> CollectionResponse:
    return CollectionResponse(
        id=dto.id,
        workspace_id=dto.workspace_id,
        name=dto.name,
        description=dto.description,
        created_at=dto.created_at,
        updated_at=dto.updated_at,
    )


def _membership_response(dto) -> CollectionMembershipResponse:
    return CollectionMembershipResponse(
        id=dto.id,
        collection_id=dto.collection_id,
        member_kind=dto.member_kind,
        member_id=dto.member_id,
        reason=dto.reason,
        added_at=dto.added_at,
    )


@router.post(
    "",
    response_model=CollectionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a collection",
)
def create_collection(
    body: CreateCollectionRequest,
    service: Annotated[CollectionService, Depends(get_collection_service)],
    workspace_id: Annotated[WorkspaceId, Depends(get_active_workspace_id)],
) -> CollectionResponse:
    try:
        with timed_operation("collections.create", attributes={"operation": "collections.create"}):
            created = service.create(
                workspace_id=workspace_id,
                name=body.name,
                description=body.description,
            )
    except (InvalidCollectionError, MemoryDomainError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    return _collection_response(created)


@router.get(
    "",
    response_model=CollectionListResponse,
    status_code=status.HTTP_200_OK,
    summary="List collections",
)
def list_collections(
    service: Annotated[CollectionService, Depends(get_collection_service)],
    workspace_id: Annotated[WorkspaceId, Depends(get_active_workspace_id)],
) -> CollectionListResponse:
    with timed_operation("collections.list", attributes={"operation": "collections.list"}):
        items = service.list(workspace_id=workspace_id)
    return CollectionListResponse(
        items=[
            CollectionListItemResponse(
                id=item.id,
                workspace_id=item.workspace_id,
                name=item.name,
                description=item.description,
                created_at=item.created_at,
                updated_at=item.updated_at,
                item_count=item.item_count,
                counts_by_kind=dict(item.counts_by_kind),
            )
            for item in items
        ],
        count=len(items),
    )


@router.get(
    "/{collection_id}",
    response_model=CollectionResponse,
    status_code=status.HTTP_200_OK,
    summary="Get a collection",
)
def get_collection(
    collection_id: str,
    service: Annotated[CollectionService, Depends(get_collection_service)],
    workspace_id: Annotated[WorkspaceId, Depends(get_active_workspace_id)],
) -> CollectionResponse:
    try:
        collection = service.get(collection_id, workspace_id=workspace_id)
    except CollectionNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return _collection_response(collection)


@router.get(
    "/{collection_id}/summary",
    response_model=CollectionSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Collection statistics and recent activity",
)
def get_collection_summary(
    collection_id: str,
    service: Annotated[CollectionService, Depends(get_collection_service)],
    workspace_id: Annotated[WorkspaceId, Depends(get_active_workspace_id)],
) -> CollectionSummaryResponse:
    try:
        summary = service.summary(collection_id, workspace_id=workspace_id)
    except CollectionNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return CollectionSummaryResponse(
        id=summary.id,
        workspace_id=summary.workspace_id,
        name=summary.name,
        description=summary.description,
        created_at=summary.created_at,
        updated_at=summary.updated_at,
        item_count=summary.item_count,
        counts_by_kind=dict(summary.counts_by_kind),
        recent_activity=[
            CollectionActivityResponse(
                activity_type=entry.activity_type,
                occurred_at=entry.occurred_at,
                member_kind=entry.member_kind,
                member_id=entry.member_id,
                detail=entry.detail,
            )
            for entry in summary.recent_activity
        ],
    )


@router.patch(
    "/{collection_id}",
    response_model=CollectionResponse,
    status_code=status.HTTP_200_OK,
    summary="Rename a collection",
)
def rename_collection(
    collection_id: str,
    body: RenameCollectionRequest,
    service: Annotated[CollectionService, Depends(get_collection_service)],
    workspace_id: Annotated[WorkspaceId, Depends(get_active_workspace_id)],
) -> CollectionResponse:
    try:
        updated = service.rename(collection_id, workspace_id=workspace_id, name=body.name)
    except CollectionNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except InvalidCollectionError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    return _collection_response(updated)


@router.patch(
    "/{collection_id}/description",
    response_model=CollectionResponse,
    status_code=status.HTTP_200_OK,
    summary="Update collection description",
)
def update_collection_description(
    collection_id: str,
    body: UpdateCollectionDescriptionRequest,
    service: Annotated[CollectionService, Depends(get_collection_service)],
    workspace_id: Annotated[WorkspaceId, Depends(get_active_workspace_id)],
) -> CollectionResponse:
    try:
        updated = service.update_description(
            collection_id,
            workspace_id=workspace_id,
            description=body.description,
        )
    except CollectionNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except InvalidCollectionError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    return _collection_response(updated)


@router.delete(
    "/{collection_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a collection",
)
def delete_collection(
    collection_id: str,
    service: Annotated[CollectionService, Depends(get_collection_service)],
    workspace_id: Annotated[WorkspaceId, Depends(get_active_workspace_id)],
) -> None:
    try:
        service.delete(collection_id, workspace_id=workspace_id)
    except CollectionNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get(
    "/{collection_id}/members",
    response_model=CollectionMembershipListResponse,
    status_code=status.HTTP_200_OK,
    summary="List collection members",
)
def list_collection_members(
    collection_id: str,
    service: Annotated[CollectionService, Depends(get_collection_service)],
    workspace_id: Annotated[WorkspaceId, Depends(get_active_workspace_id)],
    member_kind: Annotated[
        str | None,
        Query(description="Filter by member kind."),
    ] = None,
    q: Annotated[
        str | None,
        Query(description="Search member IDs, kinds, and reasons."),
    ] = None,
) -> CollectionMembershipListResponse:
    try:
        members = service.list_members(
            collection_id,
            workspace_id=workspace_id,
            member_kind=member_kind,
            query=q,
        )
    except CollectionNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except InvalidCollectionMembershipError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    return CollectionMembershipListResponse(
        items=[_membership_response(item) for item in members],
        count=len(members),
    )


@router.post(
    "/{collection_id}/members",
    response_model=CollectionMembershipResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add an item to a collection",
)
def add_collection_member(
    collection_id: str,
    body: AddCollectionMemberRequest,
    service: Annotated[CollectionService, Depends(get_collection_service)],
    workspace_id: Annotated[WorkspaceId, Depends(get_active_workspace_id)],
) -> CollectionMembershipResponse:
    try:
        membership = service.add_member(
            collection_id,
            workspace_id=workspace_id,
            member_kind=body.member_kind,
            member_id=body.member_id,
            reason=body.reason,
        )
    except CollectionNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except DuplicateCollectionMembershipError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except InvalidCollectionMembershipError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    return _membership_response(membership)


@router.delete(
    "/{collection_id}/members/{member_kind}/{member_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove an item from a collection",
)
def remove_collection_member(
    collection_id: str,
    member_kind: str,
    member_id: str,
    service: Annotated[CollectionService, Depends(get_collection_service)],
    workspace_id: Annotated[WorkspaceId, Depends(get_active_workspace_id)],
) -> None:
    try:
        service.remove_member(
            collection_id,
            workspace_id=workspace_id,
            member_kind=member_kind,
            member_id=member_id,
        )
    except CollectionNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except CollectionMembershipNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except InvalidCollectionMembershipError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
