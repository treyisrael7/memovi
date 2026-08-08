from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from memovi_observability import timed_operation
from memovi_shared import WorkspaceId

from memovi_memory.api.dependencies import get_active_workspace_id, get_tag_service
from memovi_memory.api.tag_schemas import (
    AssignTagRequest,
    CreateTagRequest,
    TagAssignmentListResponse,
    TagAssignmentResponse,
    TagListItemResponse,
    TagListResponse,
    TagResponse,
    TagSuggestResponse,
    UpdateTagRequest,
)
from memovi_memory.application.dto import TagAssignmentDto, TagDto
from memovi_memory.application.services import TagService
from memovi_memory.domain.exceptions import (
    DuplicateTagAssignmentError,
    DuplicateTagNameError,
    InvalidCollectionMembershipError,
    InvalidTagAssignmentError,
    InvalidTagError,
    MemoryDomainError,
    TagAssignmentNotFoundError,
    TagNotFoundError,
)

router = APIRouter(prefix="/tags", tags=["tags"])


def _tag_response(dto: TagDto) -> TagResponse:
    return TagResponse(
        id=dto.id,
        workspace_id=dto.workspace_id,
        name=dto.name,
        color=dto.color,
        description=dto.description,
        created_at=dto.created_at,
        updated_at=dto.updated_at,
    )


def _assignment_response(dto: TagAssignmentDto) -> TagAssignmentResponse:
    return TagAssignmentResponse(
        id=dto.id,
        tag_id=dto.tag_id,
        member_kind=dto.member_kind,
        member_id=dto.member_id,
        assigned_at=dto.assigned_at,
    )


@router.post(
    "",
    response_model=TagResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a tag",
)
def create_tag(
    body: CreateTagRequest,
    service: Annotated[TagService, Depends(get_tag_service)],
    workspace_id: Annotated[WorkspaceId, Depends(get_active_workspace_id)],
) -> TagResponse:
    try:
        with timed_operation("tags.create", attributes={"operation": "tags.create"}):
            created = service.create(
                workspace_id=workspace_id,
                name=body.name,
                color=body.color,
                description=body.description,
            )
    except DuplicateTagNameError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except (InvalidTagError, MemoryDomainError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    return _tag_response(created)


@router.get(
    "",
    response_model=TagListResponse,
    status_code=status.HTTP_200_OK,
    summary="List tags",
)
def list_tags(
    service: Annotated[TagService, Depends(get_tag_service)],
    workspace_id: Annotated[WorkspaceId, Depends(get_active_workspace_id)],
) -> TagListResponse:
    with timed_operation("tags.list", attributes={"operation": "tags.list"}):
        items = service.list(workspace_id=workspace_id)
    return TagListResponse(
        items=[
            TagListItemResponse(
                id=item.id,
                workspace_id=item.workspace_id,
                name=item.name,
                color=item.color,
                description=item.description,
                created_at=item.created_at,
                updated_at=item.updated_at,
                assignment_count=item.assignment_count,
                counts_by_kind=dict(item.counts_by_kind),
            )
            for item in items
        ],
        count=len(items),
    )


@router.get(
    "/suggest",
    response_model=TagSuggestResponse,
    status_code=status.HTTP_200_OK,
    summary="Suggest tags by name prefix",
)
def suggest_tags(
    service: Annotated[TagService, Depends(get_tag_service)],
    workspace_id: Annotated[WorkspaceId, Depends(get_active_workspace_id)],
    q: Annotated[str, Query(description="Name prefix to match.")] = "",
) -> TagSuggestResponse:
    with timed_operation("tags.suggest", attributes={"operation": "tags.suggest"}):
        items = service.suggest(workspace_id=workspace_id, query=q)
    return TagSuggestResponse(
        items=[_tag_response(item) for item in items],
        count=len(items),
    )


@router.get(
    "/for-target",
    response_model=TagSuggestResponse,
    status_code=status.HTTP_200_OK,
    summary="List tags assigned to a target resource",
)
def list_tags_for_target(
    service: Annotated[TagService, Depends(get_tag_service)],
    workspace_id: Annotated[WorkspaceId, Depends(get_active_workspace_id)],
    member_kind: Annotated[str, Query(description="Target member kind.")],
    member_id: Annotated[str, Query(description="Target member ID.")],
) -> TagSuggestResponse:
    try:
        with timed_operation("tags.for_target", attributes={"operation": "tags.for_target"}):
            items = service.list_for_target(
                workspace_id=workspace_id,
                member_kind=member_kind,
                member_id=member_id,
            )
    except InvalidCollectionMembershipError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    return TagSuggestResponse(
        items=[_tag_response(item) for item in items],
        count=len(items),
    )


@router.get(
    "/{tag_id}",
    response_model=TagResponse,
    status_code=status.HTTP_200_OK,
    summary="Get a tag",
)
def get_tag(
    tag_id: str,
    service: Annotated[TagService, Depends(get_tag_service)],
    workspace_id: Annotated[WorkspaceId, Depends(get_active_workspace_id)],
) -> TagResponse:
    try:
        tag = service.get(tag_id, workspace_id=workspace_id)
    except TagNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return _tag_response(tag)


@router.patch(
    "/{tag_id}",
    response_model=TagResponse,
    status_code=status.HTTP_200_OK,
    summary="Update a tag",
)
def update_tag(
    tag_id: str,
    body: UpdateTagRequest,
    service: Annotated[TagService, Depends(get_tag_service)],
    workspace_id: Annotated[WorkspaceId, Depends(get_active_workspace_id)],
) -> TagResponse:
    update_kwargs: dict[str, object] = {
        "name": body.name,
        "description": body.description,
    }
    if "color" in body.model_fields_set:
        update_kwargs["color"] = body.color
    try:
        updated = service.update(tag_id, workspace_id=workspace_id, **update_kwargs)
    except TagNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except DuplicateTagNameError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except InvalidTagError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    return _tag_response(updated)


@router.delete(
    "/{tag_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a tag",
)
def delete_tag(
    tag_id: str,
    service: Annotated[TagService, Depends(get_tag_service)],
    workspace_id: Annotated[WorkspaceId, Depends(get_active_workspace_id)],
) -> None:
    try:
        service.delete(tag_id, workspace_id=workspace_id)
    except TagNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get(
    "/{tag_id}/assignments",
    response_model=TagAssignmentListResponse,
    status_code=status.HTTP_200_OK,
    summary="List tag assignments",
)
def list_tag_assignments(
    tag_id: str,
    service: Annotated[TagService, Depends(get_tag_service)],
    workspace_id: Annotated[WorkspaceId, Depends(get_active_workspace_id)],
    member_kind: Annotated[
        str | None,
        Query(description="Filter by member kind."),
    ] = None,
    q: Annotated[
        str | None,
        Query(description="Search member IDs and kinds."),
    ] = None,
) -> TagAssignmentListResponse:
    try:
        assignments = service.list_assignments(
            tag_id,
            workspace_id=workspace_id,
            member_kind=member_kind,
            query=q,
        )
    except TagNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except InvalidCollectionMembershipError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    return TagAssignmentListResponse(
        items=[_assignment_response(item) for item in assignments],
        count=len(assignments),
    )


@router.post(
    "/{tag_id}/assignments",
    response_model=TagAssignmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Assign a tag to a resource",
)
def assign_tag(
    tag_id: str,
    body: AssignTagRequest,
    service: Annotated[TagService, Depends(get_tag_service)],
    workspace_id: Annotated[WorkspaceId, Depends(get_active_workspace_id)],
) -> TagAssignmentResponse:
    try:
        assignment = service.assign(
            tag_id,
            workspace_id=workspace_id,
            member_kind=body.member_kind,
            member_id=body.member_id,
        )
    except TagNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except DuplicateTagAssignmentError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except (InvalidTagAssignmentError, InvalidCollectionMembershipError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    return _assignment_response(assignment)


@router.delete(
    "/{tag_id}/assignments/{member_kind}/{member_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove a tag assignment",
)
def unassign_tag(
    tag_id: str,
    member_kind: str,
    member_id: str,
    service: Annotated[TagService, Depends(get_tag_service)],
    workspace_id: Annotated[WorkspaceId, Depends(get_active_workspace_id)],
) -> None:
    try:
        service.unassign(
            tag_id,
            workspace_id=workspace_id,
            member_kind=member_kind,
            member_id=member_id,
        )
    except TagNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except TagAssignmentNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except InvalidCollectionMembershipError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
