from threading import Lock

from memovi_shared import WorkspaceId

from memovi_automation.domain.value_objects.execution_audit_entry import ExecutionAuditEntry


class InMemoryExecutionAuditStore:
    """Process-local audit trail for capability executions."""

    def __init__(self) -> None:
        self._entries: list[ExecutionAuditEntry] = []
        self._lock = Lock()

    def append(self, entry: ExecutionAuditEntry) -> None:
        with self._lock:
            self._entries.append(entry)

    def list_for_workspace(
        self,
        *,
        workspace_id: WorkspaceId,
        limit: int = 100,
    ) -> tuple[ExecutionAuditEntry, ...]:
        with self._lock:
            matched = [entry for entry in self._entries if entry.workspace_id == workspace_id.value]
        return tuple(matched[-limit:])

    def list_for_execution(self, execution_id: str) -> tuple[ExecutionAuditEntry, ...]:
        with self._lock:
            matched = [entry for entry in self._entries if entry.execution_id == execution_id]
        return tuple(matched)
