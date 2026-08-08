"""Durable SQLAlchemy workflow execution history store."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime

from memovi_observability import get_metrics_recorder
from memovi_shared import WorkspaceId
from sqlalchemy.orm import Session as OrmSession

from memovi_automation.domain.value_objects.workflow import (
    WorkflowExecutionResult,
    WorkflowHistoryEntry,
)
from memovi_automation.infrastructure.persistence.models import WorkflowHistoryRecord
from memovi_automation.infrastructure.workflow_codec import (
    deserialize_execution_result,
    serialize_execution_result,
)

SessionFactory = Callable[[], OrmSession]

_INTERRUPTIBLE = frozenset({"running"})


class SqlAlchemyWorkflowHistoryStore:
    """Postgres/SQLite-backed workflow history and execution status."""

    def __init__(self, session_factory: SessionFactory) -> None:
        self._session_factory = session_factory

    def append(self, entry: WorkflowHistoryEntry) -> None:
        session = self._session_factory()
        try:
            record = session.get(WorkflowHistoryRecord, entry.instance_id)
            if record is None:
                session.add(
                    WorkflowHistoryRecord(
                        instance_id=entry.instance_id,
                        workflow_id=entry.workflow_id,
                        workflow_name=entry.workflow_name,
                        workspace_id=entry.workspace_id,
                        user_id=entry.user_id,
                        status=entry.status,
                        started_at=entry.executed_at,
                        completed_at=entry.completed_at,
                        duration=entry.duration,
                        result_summary=dict(entry.result_summary),
                        executed_capabilities=list(entry.executed_capabilities),
                        executed_steps=list(entry.executed_steps),
                        failed_steps=list(entry.failed_steps),
                        error_details=list(entry.error_details),
                        audit_references=list(entry.audit_references),
                        full_result=None,
                    )
                )
            else:
                self._apply_entry(record, entry)
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def list_for_workspace(
        self,
        *,
        workspace_id: WorkspaceId,
        limit: int = 100,
    ) -> tuple[WorkflowHistoryEntry, ...]:
        session = self._session_factory()
        try:
            records = (
                session.query(WorkflowHistoryRecord)
                .filter(WorkflowHistoryRecord.workspace_id == workspace_id.value)
                .order_by(WorkflowHistoryRecord.started_at.asc())
                .all()
            )
            return tuple(self._to_entry(record) for record in records[-limit:][::-1])
        finally:
            session.close()

    def get(
        self,
        instance_id: str,
        *,
        workspace_id: WorkspaceId,
    ) -> WorkflowHistoryEntry | None:
        session = self._session_factory()
        try:
            record = session.get(WorkflowHistoryRecord, instance_id)
            if record is None or record.workspace_id != workspace_id.value:
                return None
            return self._to_entry(record)
        finally:
            session.close()

    def get_result(
        self,
        instance_id: str,
        *,
        workspace_id: WorkspaceId,
    ) -> WorkflowExecutionResult | None:
        session = self._session_factory()
        try:
            record = session.get(WorkflowHistoryRecord, instance_id)
            if record is None or record.workspace_id != workspace_id.value:
                return None
            if record.full_result is None:
                return None
            return deserialize_execution_result(record.full_result)
        finally:
            session.close()

    def store_result(self, result: WorkflowExecutionResult) -> None:
        session = self._session_factory()
        try:
            record = session.get(WorkflowHistoryRecord, result.instance_id)
            user_id = _meta_user(result)
            entry_fields = {
                "workflow_id": result.workflow_id,
                "workflow_name": result.workflow_name,
                "workspace_id": result.workspace_id,
                "user_id": user_id,
                "status": result.status,
                "started_at": result.started_at,
                "completed_at": result.finished_at,
                "duration": result.duration,
                "result_summary": {
                    "status": result.status,
                    "completed_steps": list(result.completed_steps),
                    "failed_steps": list(result.failed_steps),
                    "outputs": dict(result.outputs),
                    "errors": list(result.errors),
                },
                "executed_capabilities": list(
                    dict.fromkeys(
                        step.capability_id
                        for step in result.step_results
                        if step.execution_id is not None
                    )
                ),
                "executed_steps": list(result.completed_steps),
                "failed_steps": list(result.failed_steps),
                "error_details": list(result.errors),
                "audit_references": list(result.audit_references),
                "full_result": serialize_execution_result(result),
            }
            if record is None:
                session.add(
                    WorkflowHistoryRecord(
                        instance_id=result.instance_id,
                        **entry_fields,
                    )
                )
            else:
                if record.user_id and not user_id:
                    entry_fields["user_id"] = record.user_id
                for key, value in entry_fields.items():
                    setattr(record, key, value)
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def list_by_status(
        self,
        *,
        status: str,
    ) -> tuple[WorkflowExecutionResult, ...]:
        session = self._session_factory()
        try:
            records = (
                session.query(WorkflowHistoryRecord)
                .filter(WorkflowHistoryRecord.status == status)
                .order_by(WorkflowHistoryRecord.started_at.asc())
                .all()
            )
            results: list[WorkflowExecutionResult] = []
            for record in records:
                if record.full_result is None:
                    continue
                results.append(deserialize_execution_result(record.full_result))
            return tuple(results)
        finally:
            session.close()

    def fail_interrupted_executions(
        self,
        *,
        reason: str,
    ) -> tuple[WorkflowExecutionResult, ...]:
        now = datetime.now(UTC)
        session = self._session_factory()
        recovered: list[WorkflowExecutionResult] = []
        try:
            records = (
                session.query(WorkflowHistoryRecord)
                .filter(WorkflowHistoryRecord.status.in_(tuple(_INTERRUPTIBLE)))
                .all()
            )
            for record in records:
                if record.full_result is None:
                    record.status = "failed"
                    record.completed_at = now
                    record.error_details = [*list(record.error_details or []), reason]
                    continue
                result = deserialize_execution_result(record.full_result)
                updated = WorkflowExecutionResult(
                    instance_id=result.instance_id,
                    workflow_id=result.workflow_id,
                    workflow_name=result.workflow_name,
                    workspace_id=result.workspace_id,
                    status="failed",
                    completed_steps=result.completed_steps,
                    failed_steps=result.failed_steps,
                    step_results=result.step_results,
                    duration=result.duration,
                    outputs=dict(result.outputs),
                    errors=(*result.errors, reason),
                    audit_references=result.audit_references,
                    started_at=result.started_at,
                    finished_at=now,
                    metadata={**dict(result.metadata), "recovered": True},
                )
                record.status = "failed"
                record.completed_at = now
                record.duration = updated.duration
                record.result_summary = {
                    "status": "failed",
                    "completed_steps": list(updated.completed_steps),
                    "failed_steps": list(updated.failed_steps),
                    "outputs": dict(updated.outputs),
                    "errors": list(updated.errors),
                }
                record.error_details = list(updated.errors)
                record.full_result = serialize_execution_result(updated)
                recovered.append(updated)
            session.commit()
            if recovered:
                get_metrics_recorder().increment(
                    "memovi.workflows.execution.recovered",
                    value=float(len(recovered)),
                )
            return tuple(recovered)
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def _apply_entry(
        self,
        record: WorkflowHistoryRecord,
        entry: WorkflowHistoryEntry,
    ) -> None:
        record.workflow_id = entry.workflow_id
        record.workflow_name = entry.workflow_name
        record.workspace_id = entry.workspace_id
        record.user_id = entry.user_id or record.user_id
        record.status = entry.status
        record.started_at = entry.executed_at
        record.completed_at = entry.completed_at
        record.duration = entry.duration
        record.result_summary = dict(entry.result_summary)
        record.executed_capabilities = list(entry.executed_capabilities)
        record.executed_steps = list(entry.executed_steps)
        record.failed_steps = list(entry.failed_steps)
        record.error_details = list(entry.error_details)
        record.audit_references = list(entry.audit_references)

    def _to_entry(self, record: WorkflowHistoryRecord) -> WorkflowHistoryEntry:
        return WorkflowHistoryEntry(
            instance_id=record.instance_id,
            workflow_id=record.workflow_id,
            workflow_name=record.workflow_name,
            workspace_id=record.workspace_id,
            status=record.status,
            executed_at=_as_utc(record.started_at),
            duration=record.duration,
            result_summary=dict(record.result_summary or {}),
            executed_capabilities=tuple(record.executed_capabilities or ()),
            audit_references=tuple(record.audit_references or ()),
            user_id=record.user_id,
            completed_at=None if record.completed_at is None else _as_utc(record.completed_at),
            executed_steps=tuple(record.executed_steps or ()),
            failed_steps=tuple(record.failed_steps or ()),
            error_details=tuple(record.error_details or ()),
        )


def _meta_user(result: WorkflowExecutionResult) -> str | None:
    value = result.metadata.get("user_id")
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
