from typing import Protocol

from memovi_shared import WorkspaceId

from documents.domain.entities import Document, DocumentVersion
from documents.domain.value_objects import DocumentId


class DocumentRepository(Protocol):
    """Persistence contract for normalized document use cases."""

    def get_by_id(
        self,
        document_id: DocumentId,
        *,
        workspace_id: WorkspaceId,
    ) -> Document | None:
        raise NotImplementedError

    def get_by_id_unscoped(self, document_id: DocumentId) -> Document | None:
        """Load a document by ID for trusted pipeline/system use."""
        raise NotImplementedError

    def add(self, document: Document) -> None:
        raise NotImplementedError

    def list_by_workspace(self, *, workspace_id: WorkspaceId) -> list[Document]:
        raise NotImplementedError

    def add_version(self, version: DocumentVersion) -> None:
        raise NotImplementedError

    def get_latest_version(self, document_id: DocumentId) -> DocumentVersion | None:
        raise NotImplementedError

    def get_version_by_id(self, version_id: str) -> DocumentVersion | None:
        raise NotImplementedError

    def save_version(self, version: DocumentVersion) -> None:
        raise NotImplementedError
