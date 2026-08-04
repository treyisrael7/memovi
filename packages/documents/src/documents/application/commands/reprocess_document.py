from dataclasses import dataclass

from memovi_shared import WorkspaceId

from documents.application.exceptions import DocumentNotFoundError, DocumentVersionNotFoundError
from documents.domain.entities import ProcessingJob
from documents.domain.enums import ProcessingStatus
from documents.domain.repositories import DocumentRepository, ProcessingJobRepository
from documents.domain.value_objects import DocumentId


@dataclass(frozen=True, slots=True)
class ReprocessDocumentCommand:
    document_id: str
    workspace_id: WorkspaceId


@dataclass(frozen=True, slots=True)
class ReprocessDocumentResult:
    document_id: str
    processing_job_id: str
    processing_status: ProcessingStatus


class ReprocessDocument:
    """Re-queues ingestion processing for a document's most recent stored version."""

    def __init__(
        self,
        *,
        documents: DocumentRepository,
        processing_jobs: ProcessingJobRepository,
    ) -> None:
        self._documents = documents
        self._processing_jobs = processing_jobs

    def execute(self, command: ReprocessDocumentCommand) -> ReprocessDocumentResult:
        document_id = DocumentId(command.document_id)
        document = self._documents.get_by_id(document_id, workspace_id=command.workspace_id)
        if document is None:
            raise DocumentNotFoundError("Document was not found.")

        version = self._documents.get_latest_version(document_id)
        if version is None:
            raise DocumentVersionNotFoundError(
                "Document has no stored version to reprocess.",
            )

        job = ProcessingJob.create_pending(
            document_id=document_id,
            document_version_id=version.id,
        )
        self._processing_jobs.add(job)

        return ReprocessDocumentResult(
            document_id=document_id.value,
            processing_job_id=job.id,
            processing_status=job.status,
        )
