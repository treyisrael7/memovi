"""Process-local workflow execution history."""

from __future__ import annotations

from datetime import UTC, datetime
from threading import Lock

from memovi_observability import get_metrics_recorder
from memovi_shared import WorkspaceId

from memovi_automation.domain.value_objects.workflow import (
    WorkflowExecutionResult,
    WorkflowHistoryEntry,
)

_TERMINAL = frozenset({"completed", "failed", "cancelled"})
_INTERRUPTIBLE = frozenset({"running"})


class InMemoryWorkflowHistoryStore:
    """In-memory WorkflowHistoryStore for local/dev and tests."""

    def __init__(self) -> None:
        self._entries: dict[str, WorkflowHistoryEntry] = {}
        self._results: dict[str, WorkflowExecutionResult] = {}
        self._lock = Lock()

    def append(self, entry: WorkflowHistoryEntry) -> None:
        with self._lock:
            self._entries[entry.instance_id] = entry

    def list_for_workspace(
        self,
        *,
        workspace_id: WorkspaceId,
        limit: int = 100,
    ) -> tuple[WorkflowHistoryEntry, ...]:
        with self._lock:
            matched = [
                entry
                for entry in self._entries.values()
                if entry.workspace_id == workspace_id.value
            ]
        matched.sort(key=lambda item: item.executed_at)
        return tuple(matched[-limit:][::-1])

    def get(
        self,
        instance_id: str,
        *,
        workspace_id: WorkspaceId,
    ) -> WorkflowHistoryEntry | None:
        with self._lock:
            entry = self._entries.get(instance_id)
        if entry is None or entry.workspace_id != workspace_id.value:
            return None
        return entry

    def get_result(
        self,
        instance_id: str,
        *,
        workspace_id: WorkspaceId,
    ) -> WorkflowExecutionResult | None:
        with self._lock:
            result = self._results.get(instance_id)
        if result is None or result.workspace_id != workspace_id.value:
            return None
        return result

    def store_result(self, result: WorkflowExecutionResult) -> None:
        with self._lock:
            self._results[result.instance_id] = result
            existing = self._entries.get(result.instance_id)
            self._entries[result.instance_id] = _entry_from_result(result, existing)

    def list_by_status(
        self,
        *,
        status: str,
    ) -> tuple[WorkflowExecutionResult, ...]:
        with self._lock:
            return tuple(result for result in self._results.values() if result.status == status)

    def fail_interrupted_executions(
        self,
        *,
        reason: str,
    ) -> tuple[WorkflowExecutionResult, ...]:
        now = datetime.now(UTC)
        recovered: list[WorkflowExecutionResult] = []
        with self._lock:
            for instance_id, result in list(self._results.items()):
                if result.status not in _INTERRUPTIBLE:
                    continue
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
                self._results[instance_id] = updated
                existing = self._entries.get(instance_id)
                self._entries[instance_id] = _entry_from_result(updated, existing)
                recovered.append(updated)
        if recovered:
            get_metrics_recorder().increment(
                "memovi.workflows.execution.recovered",
                value=float(len(recovered)),
            )
        return tuple(recovered)


def _entry_from_result(
    result: WorkflowExecutionResult,
    existing: WorkflowHistoryEntry | None,
) -> WorkflowHistoryEntry:
    user_id = None
    if existing is not None:
        user_id = existing.user_id
    meta_user = result.metadata.get("user_id")
    if isinstance(meta_user, str) and meta_user.strip():
        user_id = meta_user.strip()
    return WorkflowHistoryEntry(
        instance_id=result.instance_id,
        workflow_id=result.workflow_id,
        workflow_name=result.workflow_name,
        workspace_id=result.workspace_id,
        status=result.status,
        executed_at=result.started_at,
        duration=result.duration,
        result_summary={
            "status": result.status,
            "completed_steps": list(result.completed_steps),
            "failed_steps": list(result.failed_steps),
            "outputs": dict(result.outputs),
            "errors": list(result.errors),
        },
        executed_capabilities=tuple(
            dict.fromkeys(
                step.capability_id for step in result.step_results if step.execution_id is not None
            )
        ),
        audit_references=result.audit_references,
        user_id=user_id,
        completed_at=result.finished_at,
        executed_steps=result.completed_steps,
        failed_steps=result.failed_steps,
        error_details=result.errors,
    )
