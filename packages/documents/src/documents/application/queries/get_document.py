from memovi_shared import WorkspaceId

from documents.application.dto import DocumentDto
from documents.application.exceptions import DocumentNotFoundError
from documents.domain.repositories import DocumentRepository
from documents.domain.value_objects import DocumentId


class GetDocument:
    def __init__(self, *, documents: DocumentRepository) -> None:
        self._documents = documents

    def execute(self, document_id: str, *, workspace_id: WorkspaceId) -> DocumentDto:
        document = self._documents.get_by_id(
            DocumentId(document_id),
            workspace_id=workspace_id,
        )
        if document is None:
            raise DocumentNotFoundError("Document was not found.")

        return DocumentDto.from_document(document)
