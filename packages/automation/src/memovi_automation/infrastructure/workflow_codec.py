"""JSON helpers for durable workflow definitions and history."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

from memovi_automation.domain.value_objects.workflow import (
    WorkflowDefinition,
    WorkflowExecutionResult,
    WorkflowHistoryEntry,
    WorkflowStep,
    WorkflowStepResult,
    WorkflowVariable,
)
from memovi_automation.infrastructure.execution_state_codec import json_safe


def serialize_definition(definition: WorkflowDefinition) -> dict[str, object]:
    return {
        "workflow_id": definition.workflow_id,
        "name": definition.name,
        "description": definition.description,
        "version": definition.version,
        "workspace_id": definition.workspace_id,
        "steps": [serialize_step(step) for step in definition.steps],
        "variables": [serialize_variable(variable) for variable in definition.variables],
        "expected_outputs": list(definition.expected_outputs),
        "required_capabilities": list(definition.required_capabilities),
        "metadata": json_safe(dict(definition.metadata)),
        "created_at": definition.created_at.astimezone(UTC).isoformat(),
        "updated_at": definition.updated_at.astimezone(UTC).isoformat(),
    }


def deserialize_definition(payload: Mapping[str, Any]) -> WorkflowDefinition:
    steps_raw = payload.get("steps") or []
    variables_raw = payload.get("variables") or []
    return WorkflowDefinition(
        workflow_id=str(payload["workflow_id"]),
        name=str(payload["name"]),
        description=str(payload.get("description") or ""),
        steps=tuple(deserialize_step(item) for item in steps_raw),
        variables=tuple(deserialize_variable(item) for item in variables_raw),
        expected_outputs=tuple(str(item) for item in (payload.get("expected_outputs") or ())),
        required_capabilities=tuple(
            str(item) for item in (payload.get("required_capabilities") or ())
        ),
        metadata=dict(payload.get("metadata") or {}),
        version=int(payload.get("version") or 1),
        workspace_id=_optional_str(payload.get("workspace_id")),
        created_at=_parse_datetime(payload.get("created_at") or datetime.now(UTC)),
        updated_at=_parse_datetime(payload.get("updated_at") or datetime.now(UTC)),
    )


def serialize_step(step: WorkflowStep) -> dict[str, object]:
    return {
        "step_id": step.step_id,
        "capability_id": step.capability_id,
        "operation": step.operation,
        "input_mapping": json_safe(dict(step.input_mapping)),
        "output_mapping": dict(step.output_mapping),
        "expected_result": step.expected_result,
        "description": step.description,
    }


def deserialize_step(payload: Mapping[str, Any]) -> WorkflowStep:
    return WorkflowStep(
        step_id=str(payload["step_id"]),
        capability_id=str(payload["capability_id"]),
        operation=str(payload["operation"]),
        input_mapping=dict(payload.get("input_mapping") or {}),
        output_mapping={
            str(key): str(value) for key, value in dict(payload.get("output_mapping") or {}).items()
        },
        expected_result=_optional_str(payload.get("expected_result")),
        description=str(payload.get("description") or ""),
    )


def serialize_variable(variable: WorkflowVariable) -> dict[str, object]:
    return {
        "name": variable.name,
        "type": variable.type,
        "description": variable.description,
        "required": variable.required,
        "default": json_safe(variable.default),
    }


def deserialize_variable(payload: Mapping[str, Any]) -> WorkflowVariable:
    return WorkflowVariable(
        name=str(payload["name"]),
        type=str(payload.get("type") or "string"),
        description=str(payload.get("description") or ""),
        required=bool(payload.get("required", True)),
        default=payload.get("default"),
    )


def serialize_history_entry(entry: WorkflowHistoryEntry) -> dict[str, object]:
    return {
        "instance_id": entry.instance_id,
        "workflow_id": entry.workflow_id,
        "workflow_name": entry.workflow_name,
        "workspace_id": entry.workspace_id,
        "status": entry.status,
        "executed_at": entry.executed_at.astimezone(UTC).isoformat(),
        "duration": entry.duration,
        "result_summary": json_safe(dict(entry.result_summary)),
        "executed_capabilities": list(entry.executed_capabilities),
        "audit_references": list(entry.audit_references),
        "user_id": entry.user_id,
        "completed_at": (
            None
            if entry.completed_at is None
            else entry.completed_at.astimezone(UTC).isoformat()
        ),
        "executed_steps": list(entry.executed_steps),
        "failed_steps": list(entry.failed_steps),
        "error_details": list(entry.error_details),
    }


def deserialize_history_entry(payload: Mapping[str, Any]) -> WorkflowHistoryEntry:
    return WorkflowHistoryEntry(
        instance_id=str(payload["instance_id"]),
        workflow_id=str(payload["workflow_id"]),
        workflow_name=str(payload["workflow_name"]),
        workspace_id=str(payload["workspace_id"]),
        status=str(payload["status"]),
        executed_at=_parse_datetime(payload["executed_at"]),
        duration=float(payload.get("duration") or 0.0),
        result_summary=dict(payload.get("result_summary") or {}),
        executed_capabilities=tuple(
            str(item) for item in (payload.get("executed_capabilities") or ())
        ),
        audit_references=tuple(str(item) for item in (payload.get("audit_references") or ())),
        user_id=_optional_str(payload.get("user_id")),
        completed_at=(
            None
            if payload.get("completed_at") is None
            else _parse_datetime(payload["completed_at"])
        ),
        executed_steps=tuple(str(item) for item in (payload.get("executed_steps") or ())),
        failed_steps=tuple(str(item) for item in (payload.get("failed_steps") or ())),
        error_details=tuple(str(item) for item in (payload.get("error_details") or ())),
    )


def serialize_execution_result(result: WorkflowExecutionResult) -> dict[str, object]:
    return {
        "instance_id": result.instance_id,
        "workflow_id": result.workflow_id,
        "workflow_name": result.workflow_name,
        "workspace_id": result.workspace_id,
        "status": result.status,
        "completed_steps": list(result.completed_steps),
        "failed_steps": list(result.failed_steps),
        "step_results": [serialize_step_result(step) for step in result.step_results],
        "duration": result.duration,
        "outputs": json_safe(dict(result.outputs)),
        "errors": list(result.errors),
        "audit_references": list(result.audit_references),
        "started_at": result.started_at.astimezone(UTC).isoformat(),
        "finished_at": (
            None
            if result.finished_at is None
            else result.finished_at.astimezone(UTC).isoformat()
        ),
        "metadata": json_safe(dict(result.metadata)),
    }


def deserialize_execution_result(payload: Mapping[str, Any]) -> WorkflowExecutionResult:
    steps_raw = payload.get("step_results") or []
    return WorkflowExecutionResult(
        instance_id=str(payload["instance_id"]),
        workflow_id=str(payload["workflow_id"]),
        workflow_name=str(payload["workflow_name"]),
        workspace_id=str(payload["workspace_id"]),
        status=str(payload["status"]),
        completed_steps=tuple(str(item) for item in (payload.get("completed_steps") or ())),
        failed_steps=tuple(str(item) for item in (payload.get("failed_steps") or ())),
        step_results=tuple(deserialize_step_result(item) for item in steps_raw),
        duration=float(payload.get("duration") or 0.0),
        outputs=dict(payload.get("outputs") or {}),
        errors=tuple(str(item) for item in (payload.get("errors") or ())),
        audit_references=tuple(str(item) for item in (payload.get("audit_references") or ())),
        started_at=_parse_datetime(payload.get("started_at") or datetime.now(UTC)),
        finished_at=(
            None
            if payload.get("finished_at") is None
            else _parse_datetime(payload["finished_at"])
        ),
        metadata=dict(payload.get("metadata") or {}),
    )


def serialize_step_result(step: WorkflowStepResult) -> dict[str, object]:
    return {
        "step_id": step.step_id,
        "capability_id": step.capability_id,
        "operation": step.operation,
        "execution_id": step.execution_id,
        "status": step.status,
        "output": json_safe(step.output),
        "error_code": step.error_code,
        "error_message": step.error_message,
        "duration": step.duration,
        "plan_id": step.plan_id,
    }


def deserialize_step_result(payload: Mapping[str, Any]) -> WorkflowStepResult:
    return WorkflowStepResult(
        step_id=str(payload["step_id"]),
        capability_id=str(payload["capability_id"]),
        operation=str(payload["operation"]),
        execution_id=_optional_str(payload.get("execution_id")),
        status=str(payload["status"]),
        output=payload.get("output"),
        error_code=_optional_str(payload.get("error_code")),
        error_message=_optional_str(payload.get("error_message")),
        duration=float(payload.get("duration") or 0.0),
        plan_id=_optional_str(payload.get("plan_id")),
    )


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _parse_datetime(value: object) -> datetime:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)
    text = str(value)
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)
