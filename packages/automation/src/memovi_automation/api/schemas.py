from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class CapabilityParameterResponse(BaseModel):
    name: str
    type: str
    description: str
    required: bool


class CapabilityMetadataResponse(BaseModel):
    id: str
    description: str
    permissions: list[str]
    parameters: list[CapabilityParameterResponse]
    permission_mode: str


class CapabilityListResponse(BaseModel):
    items: list[CapabilityMetadataResponse]
    count: int


class SubmitCapabilityExecutionRequest(BaseModel):
    capability_id: str = Field(min_length=1)
    arguments: dict[str, Any] = Field(default_factory=dict)
    conversation_id: str | None = None
    correlation_id: str | None = None
    permission_mode: Literal["always_allow", "ask_every_time", "deny"] | None = None
    timeout_seconds: float | None = Field(default=None, gt=0)


class CapabilityErrorResponse(BaseModel):
    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class CapabilityExecutionResponse(BaseModel):
    execution_id: str
    capability_id: str
    workspace_id: str
    status: str
    permission_mode: str
    output: Any | None = None
    error: CapabilityErrorResponse | None = None
    duration: float
    conversation_id: str | None = None
    correlation_id: str | None = None
    created_at: datetime
    updated_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)


class CapabilityExecutionListResponse(BaseModel):
    items: list[CapabilityExecutionResponse]
    count: int


class SetPermissionModeRequest(BaseModel):
    permission_mode: Literal["always_allow", "ask_every_time", "deny"]


class PermissionModeResponse(BaseModel):
    capability_id: str
    permission_mode: str


class ExecutionAuditEntryResponse(BaseModel):
    id: str
    execution_id: str
    workspace_id: str
    capability_id: str
    status: str
    permission_mode: str
    arguments: dict[str, Any]
    result_summary: dict[str, Any]
    duration: float
    timestamp: datetime
    conversation_id: str | None = None
    correlation_id: str | None = None
    source: str


class ExecutionAuditListResponse(BaseModel):
    items: list[ExecutionAuditEntryResponse]
    count: int
