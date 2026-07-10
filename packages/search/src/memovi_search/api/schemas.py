from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class SearchDocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    document_id: str
    document_version_id: str
    chunk_id: str
    created_at: datetime
    updated_at: datetime


class EmbeddingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    search_document_id: str
    model_id: str
    dimensions: int = Field(gt=0)
    created_at: datetime


class SearchDocumentListResponse(BaseModel):
    items: list[SearchDocumentResponse]
