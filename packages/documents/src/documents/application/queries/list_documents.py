from memovi_shared import WorkspaceId

from documents.application.dto import DocumentDto
from documents.domain.repositories import DocumentRepository


class ListDocuments:
    def __init__(self, *, documents: DocumentRepository) -> None:
        self._documents = documents

    def execute(self, *, workspace_id: WorkspaceId) -> list[DocumentDto]:
        return [
            DocumentDto.from_document(document)
            for document in self._documents.list_by_workspace(workspace_id=workspace_id)
        ]
