import builtins
from typing import Protocol

from memovi_search.domain.entities import Embedding, RankedSearchDocument, SearchDocument
from memovi_search.domain.value_objects import EmbeddingId, SearchDocumentId


class SearchRepository(Protocol):
    """Persistence contract for searchable documents and embeddings."""

    def save_document(self, search_document: SearchDocument) -> None:
        raise NotImplementedError

    def get_document(self, search_document_id: SearchDocumentId) -> SearchDocument | None:
        raise NotImplementedError

    def list_documents(self) -> builtins.list[SearchDocument]:
        raise NotImplementedError

    def delete_document(self, search_document_id: SearchDocumentId) -> None:
        raise NotImplementedError

    def search(self, query: str, limit: int, offset: int) -> builtins.list[RankedSearchDocument]:
        raise NotImplementedError

    def save_embedding(self, embedding: Embedding) -> None:
        raise NotImplementedError

    def get_embedding(self, embedding_id: EmbeddingId) -> Embedding | None:
        raise NotImplementedError

    def delete_embedding(self, embedding_id: EmbeddingId) -> None:
        raise NotImplementedError
