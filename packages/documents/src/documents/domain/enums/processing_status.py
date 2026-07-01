from enum import StrEnum


class ProcessingStatus(StrEnum):
    """Lifecycle states for document ingestion processing."""

    PENDING = "pending"
    EXTRACTING = "extracting"
    NORMALIZING = "normalizing"
    COMPLETED = "completed"
    FAILED = "failed"
