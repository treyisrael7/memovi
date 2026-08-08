from datetime import datetime

from pydantic import BaseModel, Field


class CreateTagRequest(BaseModel):
    name: str = Field(min_length=1, max_length=256)
    color: str | None = Field(default=None, max_length=64)
    description: str = Field(default="", max_length=4000)


class UpdateTagRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=256)
    color: str | None = Field(default=None, max_length=64)
    description: str | None = Field(default=None, max_length=4000)


class AssignTagRequest(BaseModel):
    member_kind: str = Field(
        description="One of: document, knowledge, conversation, workflow.",
    )
    member_id: str = Field(min_length=1, max_length=256)


class TagResponse(BaseModel):
    id: str
    workspace_id: str
    name: str
    color: str | None = None
    description: str
    created_at: datetime
    updated_at: datetime


class TagListItemResponse(BaseModel):
    id: str
    workspace_id: str
    name: str
    color: str | None = None
    description: str
    created_at: datetime
    updated_at: datetime
    assignment_count: int
    counts_by_kind: dict[str, int]


class TagListResponse(BaseModel):
    items: list[TagListItemResponse]
    count: int


class TagSuggestResponse(BaseModel):
    items: list[TagResponse]
    count: int


class TagAssignmentResponse(BaseModel):
    id: str
    tag_id: str
    member_kind: str
    member_id: str
    assigned_at: datetime


class TagAssignmentListResponse(BaseModel):
    items: list[TagAssignmentResponse]
    count: int


class UpsertResourceMetadataRequest(BaseModel):
    title: str | None = Field(default=None, max_length=512)
    description: str | None = Field(default=None, max_length=4000)
    notes: str | None = Field(default=None, max_length=8000)


class ResourceMetadataResponse(BaseModel):
    workspace_id: str
    member_kind: str
    member_id: str
    title: str | None = None
    description: str | None = None
    notes: str | None = None
    updated_at: datetime
