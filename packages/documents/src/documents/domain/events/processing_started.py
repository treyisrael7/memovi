from dataclasses import dataclass
from datetime import datetime

from documents.domain.value_objects import DocumentId


@dataclass(frozen=True, slots=True)
class ProcessingStarted:
    """Domain fact emitted when ingestion processing begins."""

    document_id: DocumentId
    processing_job_id: str
    occurred_at: datetime
