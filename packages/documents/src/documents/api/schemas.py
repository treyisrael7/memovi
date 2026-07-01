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


class DocumentListResponse(BaseModel):
    items: list[DocumentResponse]
