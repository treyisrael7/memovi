from enum import StrEnum


class ProcessingStatus(StrEnum):
    """Lifecycle states for document ingestion processing.

    Queue-oriented view:
    - pending → waiting to run
    - extracting / normalizing → running stages
    - completed / failed / cancelled → terminal
    """

    PENDING = "pending"
    EXTRACTING = "extracting"
    NORMALIZING = "normalizing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
