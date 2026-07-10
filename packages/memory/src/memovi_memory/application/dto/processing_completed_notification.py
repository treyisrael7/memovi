from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class ProcessingCompletedNotification:
    """Cross-domain notification that document processing finished successfully."""

    document_id: str
    processing_job_id: str
    occurred_at: datetime
