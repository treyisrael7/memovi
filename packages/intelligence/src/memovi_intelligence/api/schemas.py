from datetime import datetime
from typing import Annotated, Any

from pydantic import AfterValidator, BaseModel, Field


def _require_non_blank_message(value: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError("must not be empty")
    return normalized


def _require_non_blank_title(value: str) -> str:
    normalized = " ".join(value.split())
    if not normalized:
        raise ValueError("must not be empty")
    return normalized


NonBlankMessage = Annotated[str, AfterValidator(_require_non_blank_message)]
NonBlankTitle = Annotated[str, AfterValidator(_require_non_blank_title)]


class CreateConversationResponse(BaseModel):
    conversation_id: str
    title: str
    created_at: datetime


class ConversationSummaryResponse(BaseModel):
    conversation_id: str
    title: str
    created_at: datetime
    updated_at: datetime
    message_count: int = Field(ge=0)


class ConversationListResponse(BaseModel):
    conversations: list[ConversationSummaryResponse]


class ConversationMetadataResponse(BaseModel):
    conversation_id: str
    title: str
    created_at: datetime
    updated_at: datetime
    message_count: int = Field(ge=0)


class RenameConversationRequest(BaseModel):
    title: NonBlankTitle = Field(min_length=1, max_length=200)


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
    provider: str | None = Field(default=None, max_length=64)
    model: str | None = Field(default=None, max_length=128)


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
    title: str | None = None
    execution: ExecutionMetadataResponse


class AvailableModelResponse(BaseModel):
    provider: str
    model: str
    label: str


class AvailableModelsResponse(BaseModel):
    default_provider: str
    default_model: str
    models: list[AvailableModelResponse]


class RequestCapabilityExecutionBody(BaseModel):
    capability_id: str = Field(min_length=1, max_length=128)
    arguments: dict[str, Any] = Field(default_factory=dict)
    permission_mode: str | None = Field(default=None, max_length=32)
    correlation_id: str | None = Field(default=None, max_length=128)


class ConversationCapabilityExecutionResponse(BaseModel):
    execution_id: str
    capability_id: str
    workspace_id: str
    status: str
    permission_mode: str
    output: Any | None = None
    error_code: str | None = None
    error_message: str | None = None
    duration: float
    conversation_id: str | None = None
    created_at: datetime
    updated_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)


class ConversationCapabilityExecutionListResponse(BaseModel):
    conversation_id: str
    items: list[ConversationCapabilityExecutionResponse]
    count: int
