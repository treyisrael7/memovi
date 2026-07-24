from enum import StrEnum


class CapabilityExecutionStatus(StrEnum):
    """Lifecycle states for a capability execution."""

    PENDING_APPROVAL = "pending_approval"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
