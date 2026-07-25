"""Process-local workflow execution history."""

from __future__ import annotations

from threading import Lock

from memovi_shared import WorkspaceId

from memovi_automation.domain.value_objects.workflow import (
    WorkflowExecutionResult,
    WorkflowHistoryEntry,
)


class InMemoryWorkflowHistoryStore:
    """In-memory WorkflowHistoryStore for local/dev and tests."""

    def __init__(self) -> None:
        self._entries: list[WorkflowHistoryEntry] = []
        self._results: dict[str, WorkflowExecutionResult] = {}
        self._lock = Lock()

    def append(self, entry: WorkflowHistoryEntry) -> None:
        with self._lock:
            self._entries.append(entry)

    def list_for_workspace(
        self,
        *,
        workspace_id: WorkspaceId,
        limit: int = 100,
    ) -> tuple[WorkflowHistoryEntry, ...]:
        with self._lock:
            matched = [
                entry
                for entry in self._entries
                if entry.workspace_id == workspace_id.value
            ]
        return tuple(matched[-limit:][::-1])

    def get(
        self,
        instance_id: str,
        *,
        workspace_id: WorkspaceId,
    ) -> WorkflowHistoryEntry | None:
        with self._lock:
            for entry in reversed(self._entries):
                if (
                    entry.instance_id == instance_id
                    and entry.workspace_id == workspace_id.value
                ):
                    return entry
        return None

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
