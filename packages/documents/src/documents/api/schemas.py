from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CreateDocumentRequest(BaseModel):
    name: str = Field(min_length=1, max_length=512)
    mime_type: str = Field(min_length=3, max_length=255)
    source_type: str = Field(min_length=1, max_length=64)


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    mime_type: str
    source_type: str
    created_at: datetime
    processing_status: str | None = None
    processing_failure_reason: str | None = None
    processing_updated_at: datetime | None = None
    processing_attempt: int | None = None
    processing_started_at: datetime | None = None
    processing_completed_at: datetime | None = None


class DocumentListResponse(BaseModel):
    items: list[DocumentResponse]


class IngestDocumentResponse(BaseModel):
    document_id: str
    processing_job_id: str
    processing_status: str


class ReprocessDocumentResponse(BaseModel):
    document_id: str
    processing_job_id: str
    processing_status: str
