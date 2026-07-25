"""Infrastructure adapters for capability execution (stores, future persistence)."""

from memovi_automation.infrastructure.in_memory_execution_audit_store import (
    InMemoryExecutionAuditStore,
)
from memovi_automation.infrastructure.in_memory_permission_policy_store import (
    InMemoryPermissionPolicyStore,
)
from memovi_automation.infrastructure.in_memory_workflow_history_store import (
    InMemoryWorkflowHistoryStore,
)
from memovi_automation.infrastructure.in_memory_workflow_library import (
    InMemoryWorkflowLibrary,
    built_in_workflows,
)

__all__ = [
    "InMemoryExecutionAuditStore",
    "InMemoryPermissionPolicyStore",
    "InMemoryWorkflowHistoryStore",
    "InMemoryWorkflowLibrary",
    "built_in_workflows",
]
