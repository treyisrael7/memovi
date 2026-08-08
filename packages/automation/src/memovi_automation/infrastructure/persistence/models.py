from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class CapabilityPermissionPolicyRecord(Base):
    """Durable server-owned capability permission policy."""

    __tablename__ = "automation_capability_policies"

    workspace_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    capability_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    permission_mode: Mapped[str] = mapped_column(String(32), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ExecutionAuditRecord(Base):
    """Durable capability execution audit entry."""

    __tablename__ = "automation_execution_audits"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    execution_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    workspace_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    user_id: Mapped[str | None] = mapped_column(String(36), index=True, nullable=True)
    capability_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    operation: Mapped[str | None] = mapped_column(String(128), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    permission_mode: Mapped[str] = mapped_column(String(32), nullable=False)
    arguments: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    result_summary: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    duration: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, nullable=False)
    conversation_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    correlation_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    source: Mapped[str] = mapped_column(String(64), nullable=False, default="api")


class CapabilityExecutionRecord(Base):
    """Durable live capability execution state (including pending approvals)."""

    __tablename__ = "automation_capability_executions"

    execution_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    user_id: Mapped[str | None] = mapped_column(String(36), index=True, nullable=True)
    session_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    capability_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    permission_mode: Mapped[str] = mapped_column(String(32), nullable=False)
    conversation_id: Mapped[str | None] = mapped_column(String(36), index=True, nullable=True)
    correlation_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    source: Mapped[str] = mapped_column(String(64), nullable=False, default="api")
    duration: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    output: Mapped[Any] = mapped_column(JSON, nullable=True)
    error: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSON,
        nullable=False,
        default=dict,
    )
    pending_request: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    pending_auth: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    failure_details: Mapped[str | None] = mapped_column(Text, nullable=True)


class WorkflowDefinitionRecord(Base):
    """Durable reusable workflow definition."""

    __tablename__ = "automation_workflow_definitions"

    workflow_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    workspace_id: Mapped[str | None] = mapped_column(String(36), index=True, nullable=True)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    steps: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    variables: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    expected_outputs: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    required_capabilities: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSON,
        nullable=False,
        default=dict,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class WorkflowHistoryRecord(Base):
    """Durable workflow execution history and live execution status."""

    __tablename__ = "automation_workflow_history"

    instance_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    workflow_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    workflow_name: Mapped[str] = mapped_column(String(256), nullable=False)
    workspace_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    user_id: Mapped[str | None] = mapped_column(String(36), index=True, nullable=True)
    status: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    result_summary: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    executed_capabilities: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    executed_steps: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    failed_steps: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    error_details: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    audit_references: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    full_result: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
