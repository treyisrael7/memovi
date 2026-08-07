from datetime import datetime

from pydantic import BaseModel, Field


class CreateCollectionRequest(BaseModel):
    name: str = Field(min_length=1, max_length=256)
    description: str = Field(default="", max_length=4000)


class RenameCollectionRequest(BaseModel):
    name: str = Field(min_length=1, max_length=256)


class UpdateCollectionDescriptionRequest(BaseModel):
    description: str = Field(default="", max_length=4000)


class AddCollectionMemberRequest(BaseModel):
    member_kind: str = Field(
        description="One of: document, knowledge, conversation, workflow.",
    )
    member_id: str = Field(min_length=1, max_length=256)
    reason: str = Field(
        default="Added by user",
        max_length=500,
        description="Why this item belongs in the collection.",
    )


class CollectionResponse(BaseModel):
    id: str
    workspace_id: str
    name: str
    description: str
    created_at: datetime
    updated_at: datetime


class CollectionListItemResponse(BaseModel):
    id: str
    workspace_id: str
    name: str
    description: str
    created_at: datetime
    updated_at: datetime
    item_count: int
    counts_by_kind: dict[str, int]


class CollectionListResponse(BaseModel):
    items: list[CollectionListItemResponse]
    count: int


class CollectionActivityResponse(BaseModel):
    activity_type: str
    occurred_at: datetime
    member_kind: str | None = None
    member_id: str | None = None
    detail: str = ""


class CollectionSummaryResponse(BaseModel):
    id: str
    workspace_id: str
    name: str
    description: str
    created_at: datetime
    updated_at: datetime
    item_count: int
    counts_by_kind: dict[str, int]
    recent_activity: list[CollectionActivityResponse]


class CollectionMembershipResponse(BaseModel):
    id: str
    collection_id: str
    member_kind: str
    member_id: str
    reason: str
    added_at: datetime


class CollectionMembershipListResponse(BaseModel):
    items: list[CollectionMembershipResponse]
    count: int
