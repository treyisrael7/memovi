"""HTTP schemas for the Workflow Automation API."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class WorkflowVariableResponse(BaseModel):
    name: str
    type: str
    description: str
    required: bool
    default: Any | None = None


class WorkflowStepResponse(BaseModel):
    step_id: str
    capability_id: str
    operation: str
    input_mapping: dict[str, Any] = Field(default_factory=dict)
    output_mapping: dict[str, str] = Field(default_factory=dict)
    expected_result: str | None = None
    description: str = ""


class WorkflowDefinitionResponse(BaseModel):
    workflow_id: str
    name: str
    description: str
    steps: list[WorkflowStepResponse]
    variables: list[WorkflowVariableResponse]
    required_capabilities: list[str]
    expected_outputs: list[str]
    metadata: dict[str, Any] = Field(default_factory=dict)


class WorkflowListResponse(BaseModel):
    items: list[WorkflowDefinitionResponse]
    count: int


class ExecuteWorkflowRequest(BaseModel):
    variables: dict[str, Any] = Field(default_factory=dict)
    conversation_id: str | None = None
    correlation_id: str | None = None


class WorkflowStepResultResponse(BaseModel):
    step_id: str
    capability_id: str
    operation: str
    execution_id: str | None
    status: str
    output: Any | None = None
    error_code: str | None = None
    error_message: str | None = None
    duration: float = 0.0
    plan_id: str | None = None


class WorkflowExecutionResultResponse(BaseModel):
    instance_id: str
    workflow_id: str
    workflow_name: str
    workspace_id: str
    status: str
    completed_steps: list[str]
    failed_steps: list[str]
    step_results: list[WorkflowStepResultResponse]
    duration: float
    outputs: dict[str, Any]
    errors: list[str]
    audit_references: list[str]
    started_at: datetime
    finished_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class WorkflowHistoryEntryResponse(BaseModel):
    instance_id: str
    workflow_id: str
    workflow_name: str
    workspace_id: str
    status: str
    executed_at: datetime
    duration: float
    result_summary: dict[str, Any]
    executed_capabilities: list[str]
    audit_references: list[str] = Field(default_factory=list)


class WorkflowHistoryListResponse(BaseModel):
    items: list[WorkflowHistoryEntryResponse]
    count: int
