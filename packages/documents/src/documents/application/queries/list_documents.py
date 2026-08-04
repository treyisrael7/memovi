from memovi_shared import WorkspaceId

from documents.application.dto import DocumentDto
from documents.domain.repositories import DocumentRepository, ProcessingJobRepository


class ListDocuments:
    def __init__(
        self,
        *,
        documents: DocumentRepository,
        processing_jobs: ProcessingJobRepository | None = None,
    ) -> None:
        self._documents = documents
        self._processing_jobs = processing_jobs

    def execute(self, *, workspace_id: WorkspaceId) -> list[DocumentDto]:
        documents = self._documents.list_by_workspace(workspace_id=workspace_id)
        jobs_by_document = (
            self._processing_jobs.get_latest_by_document_ids(
                [document.id for document in documents],
            )
            if self._processing_jobs is not None
            else {}
        )
        return [
            DocumentDto.from_document(
                document,
                processing_job=jobs_by_document.get(document.id.value),
            )
            for document in documents
        ]
