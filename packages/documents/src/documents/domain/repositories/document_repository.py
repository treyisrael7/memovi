from typing import Protocol

from documents.domain.entities import Document, DocumentVersion
from documents.domain.value_objects import DocumentId


class DocumentRepository(Protocol):
    """Persistence contract for normalized document use cases."""

    def get_by_id(self, document_id: DocumentId) -> Document | None:
        raise NotImplementedError

    def add(self, document: Document) -> None:
        raise NotImplementedError

    def list_all(self) -> list[Document]:
        raise NotImplementedError

    def add_version(self, version: DocumentVersion) -> None:
        raise NotImplementedError

    def get_latest_version(self, document_id: DocumentId) -> DocumentVersion | None:
        raise NotImplementedError
