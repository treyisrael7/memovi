from dataclasses import dataclass
from datetime import datetime

from documents.domain.value_objects import DocumentId


@dataclass(frozen=True, slots=True)
class ProcessingFailed:
    """Domain fact emitted when ingestion processing terminates with failure."""

    document_id: DocumentId
    processing_job_id: str
    occurred_at: datetime
    reason: str | None = None
