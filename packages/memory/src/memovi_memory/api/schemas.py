from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class KnowledgeItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    document_id: str
    document_version_id: str
    created_at: datetime
    updated_at: datetime


class ChunkResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    knowledge_item_id: str | None = None
    document_id: str
    document_version_id: str
    chunk_index: int = Field(ge=0)
    text: str
    created_at: datetime


class KnowledgeItemListResponse(BaseModel):
    items: list[KnowledgeItemResponse]
