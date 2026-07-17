from datetime import datetime
from typing import Annotated, Any

from pydantic import AfterValidator, BaseModel, Field


def _require_non_blank_message(value: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError("must not be empty")
    return normalized


NonBlankMessage = Annotated[str, AfterValidator(_require_non_blank_message)]


class CreateConversationResponse(BaseModel):
    conversation_id: str
    created_at: datetime


class ConversationMetadataResponse(BaseModel):
    conversation_id: str
    created_at: datetime
    updated_at: datetime
    message_count: int = Field(ge=0)


class CitationResponse(BaseModel):
    document_id: str
    chunk_id: str
    document_title: str | None = None
    score: float | None = None


class ConversationMessageResponse(BaseModel):
    role: str
    content: str
    timestamp: datetime
    citations: list[CitationResponse] = Field(default_factory=list)


class ConversationMessagesResponse(BaseModel):
    conversation_id: str
    messages: list[ConversationMessageResponse]


class SendMessageRequest(BaseModel):
    message: NonBlankMessage = Field(min_length=1, max_length=8_000)


class StageTimingResponse(BaseModel):
    stage: str
    started_at: datetime
    finished_at: datetime
    duration: float


class ExecutionMetricsResponse(BaseModel):
    provider: str
    model: str
    estimated_input_tokens: int
    output_tokens: int | None = None
    retrieved_knowledge_count: int
    document_count: int
    citation_count: int


class ExecutionMetadataResponse(BaseModel):
    execution_time: float
    stages: list[StageTimingResponse]
    metrics: ExecutionMetricsResponse
    metadata: dict[str, Any] = Field(default_factory=dict)


class SendMessageResponse(BaseModel):
    conversation_id: str
    assistant_message: str
    citations: list[CitationResponse]
    provider: str
    model: str
    execution: ExecutionMetadataResponse
