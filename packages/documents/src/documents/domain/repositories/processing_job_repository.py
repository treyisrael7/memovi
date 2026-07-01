from typing import Protocol

from documents.domain.entities import ProcessingJob
from documents.domain.value_objects import DocumentId


class ProcessingJobRepository(Protocol):
    """Persistence contract for document ingestion processing jobs."""

    def get_by_id(self, job_id: str) -> ProcessingJob | None:
        raise NotImplementedError

    def get_by_document_id(self, document_id: DocumentId) -> ProcessingJob | None:
        raise NotImplementedError

    def add(self, job: ProcessingJob) -> None:
        raise NotImplementedError

    def save(self, job: ProcessingJob) -> None:
        raise NotImplementedError
