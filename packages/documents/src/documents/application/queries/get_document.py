from memovi_shared import WorkspaceId

from documents.application.dto import DocumentDto
from documents.application.exceptions import DocumentNotFoundError
from documents.domain.repositories import DocumentRepository, ProcessingJobRepository
from documents.domain.value_objects import DocumentId


class GetDocument:
    def __init__(
        self,
        *,
        documents: DocumentRepository,
        processing_jobs: ProcessingJobRepository | None = None,
    ) -> None:
        self._documents = documents
        self._processing_jobs = processing_jobs

    def execute(self, document_id: str, *, workspace_id: WorkspaceId) -> DocumentDto:
        resolved_id = DocumentId(document_id)
        document = self._documents.get_by_id(resolved_id, workspace_id=workspace_id)
        if document is None:
            raise DocumentNotFoundError("Document was not found.")

        processing_job = (
            self._processing_jobs.get_by_document_id(resolved_id)
            if self._processing_jobs is not None
            else None
        )
        return DocumentDto.from_document(document, processing_job=processing_job)
