from typing import Protocol

from memovi_search.domain.entities import Embedding
from memovi_search.domain.value_objects import EmbeddingId, SearchDocumentId


class EmbeddingRepository(Protocol):
    """Persistence contract for search-document embedding projections."""

    def save(self, embedding: Embedding) -> None:
        raise NotImplementedError

    def get_by_search_document(
        self,
        search_document_id: SearchDocumentId,
    ) -> Embedding | None:
        raise NotImplementedError

    def delete(self, embedding_id: EmbeddingId) -> None:
        raise NotImplementedError
