import builtins
from datetime import datetime
from typing import Protocol

from memovi_shared import WorkspaceId

from memovi_search.domain.entities import RankedSearchDocument, SearchDocument
from memovi_search.domain.value_objects import SearchDocumentId


class SearchRepository(Protocol):
    """Persistence contract for searchable documents."""

    def save_document(self, search_document: SearchDocument) -> None:
        raise NotImplementedError

    def get_document(
        self,
        search_document_id: SearchDocumentId,
        *,
        workspace_id: WorkspaceId | None = None,
    ) -> SearchDocument | None:
        raise NotImplementedError

    def list_documents(self, *, workspace_id: WorkspaceId) -> builtins.list[SearchDocument]:
        raise NotImplementedError

    def delete_document(
        self,
        search_document_id: SearchDocumentId,
        *,
        workspace_id: WorkspaceId | None = None,
    ) -> None:
        raise NotImplementedError

    def search(
        self,
        query: str,
        limit: int,
        offset: int,
        *,
        workspace_id: WorkspaceId,
        document_id: str | None = None,
        document_version_id: str | None = None,
        source_type: str | None = None,
        mime_type: str | None = None,
        created_after: datetime | None = None,
        created_before: datetime | None = None,
    ) -> builtins.list[RankedSearchDocument]:
        raise NotImplementedError
