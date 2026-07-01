from documents.application.dto import DocumentDto
from documents.domain.repositories import DocumentRepository


class ListDocuments:
    def __init__(self, *, documents: DocumentRepository) -> None:
        self._documents = documents

    def execute(self) -> list[DocumentDto]:
        return [DocumentDto.from_document(document) for document in self._documents.list_all()]
