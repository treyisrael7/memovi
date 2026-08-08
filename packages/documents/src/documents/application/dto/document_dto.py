from dataclasses import dataclass
from datetime import datetime

from documents.domain.entities import Document, ProcessingJob


@dataclass(frozen=True, slots=True)
class DocumentDto:
    id: str
    workspace_id: str
    name: str
    mime_type: str
    source_type: str
    created_at: datetime
    processing_status: str | None = None
    processing_failure_reason: str | None = None
    processing_updated_at: datetime | None = None
    processing_attempt: int | None = None
    processing_started_at: datetime | None = None
    processing_completed_at: datetime | None = None

    @classmethod
    def from_document(
        cls,
        document: Document,
        *,
        processing_job: ProcessingJob | None = None,
    ) -> DocumentDto:
        return cls(
            id=document.id.value,
            workspace_id=document.workspace_id.value,
            name=document.name.value,
            mime_type=document.mime_type.value,
            source_type=document.source_type.value,
            created_at=document.created_at,
            processing_status=processing_job.status.value if processing_job else None,
            processing_failure_reason=(
                processing_job.failure_reason if processing_job else None
            ),
            processing_updated_at=processing_job.updated_at if processing_job else None,
            processing_attempt=processing_job.attempt if processing_job else None,
            processing_started_at=processing_job.started_at if processing_job else None,
            processing_completed_at=processing_job.completed_at if processing_job else None,
        )
