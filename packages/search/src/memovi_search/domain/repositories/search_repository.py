import builtins
from typing import Protocol

from memovi_search.domain.entities import Embedding, SearchDocument
from memovi_search.domain.value_objects import EmbeddingId, SearchDocumentId


class SearchRepository(Protocol):
    """Persistence contract for searchable documents and embedding metadata."""

    def save_search_document(self, search_document: SearchDocument) -> None:
        raise NotImplementedError

    def get_search_document(
        self,
        search_document_id: SearchDocumentId,
    ) -> SearchDocument | None:
        raise NotImplementedError

    def list_search_documents_by_document(
        self,
        *,
        document_id: str,
    ) -> builtins.list[SearchDocument]:
        raise NotImplementedError

    def list_search_documents_by_chunk(
        self,
        *,
        chunk_id: str,
    ) -> builtins.list[SearchDocument]:
        raise NotImplementedError

    def delete_search_document(self, search_document_id: SearchDocumentId) -> None:
        raise NotImplementedError

    def save_embedding(self, embedding: Embedding) -> None:
        raise NotImplementedError

    def get_embedding(self, embedding_id: EmbeddingId) -> Embedding | None:
        raise NotImplementedError

    def list_embeddings_for_search_document(
        self,
        *,
        search_document_id: SearchDocumentId,
    ) -> builtins.list[Embedding]:
        raise NotImplementedError

    def delete_embedding(self, embedding_id: EmbeddingId) -> None:
        raise NotImplementedError
