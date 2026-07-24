from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class KnowledgeItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    document_id: str
    document_version_id: str
    source_type: str
    mime_type: str
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


class KnowledgeSummaryResponse(BaseModel):
    """Inspectable knowledge entity summary for explorer lists."""

    id: str
    workspace_id: str
    document_id: str
    document_version_id: str
    source_type: str
    mime_type: str
    created_at: datetime
    updated_at: datetime
    chunk_count: int
    summary: str
    confidence: float | None = None


class KnowledgeSummaryListResponse(BaseModel):
    items: list[KnowledgeSummaryResponse]
    count: int


class KnowledgeDetailResponse(BaseModel):
    """Full knowledge item with chunks and provenance fields."""

    id: str
    workspace_id: str
    document_id: str
    document_version_id: str
    source_type: str
    mime_type: str
    created_at: datetime
    updated_at: datetime
    summary: str
    confidence: float | None = None
    chunks: list[ChunkResponse]


class ConceptResponse(BaseModel):
    id: str
    kind: str
    label: str
    knowledge_item_count: int
    knowledge_item_ids: list[str]


class ConceptListResponse(BaseModel):
    items: list[ConceptResponse]
    count: int


class RelationshipResponse(BaseModel):
    id: str
    relationship_type: str
    from_kind: str
    from_id: str
    to_kind: str
    to_id: str
    workspace_id: str
    document_id: str
    knowledge_item_id: str | None = None
    created_at: datetime


class RelationshipListResponse(BaseModel):
    items: list[RelationshipResponse]
    count: int


class KnowledgeDashboardResponse(BaseModel):
    workspace_id: str
    knowledge_item_count: int
    chunk_count: int
    source_document_count: int
    concept_count: int
    relationship_count: int
    source_type_counts: dict[str, int]
    mime_type_counts: dict[str, int]
