from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class SearchDocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    knowledge_item_id: str
    document_id: str
    document_version_id: str
    searchable_text: str
    created_at: datetime
    updated_at: datetime


class EmbeddingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    search_document_id: str
    provider: str
    model: str
    dimensions: int = Field(gt=0)
    vector: list[float]


class SearchDocumentListResponse(BaseModel):
    items: list[SearchDocumentResponse]


class SearchResultItemResponse(BaseModel):
    """A single ranked full-text search match."""

    search_document_id: str
    knowledge_item_id: str
    document_id: str
    score: float
    text: str


class SearchResponse(BaseModel):
    """Ranked full-text search response for indexed knowledge."""

    query: str
    count: int = Field(ge=0)
    results: list[SearchResultItemResponse]
