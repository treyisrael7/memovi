from memovi_search.domain.entities.search_result import SearchResult
from memovi_search.domain.providers import EmbeddingProvider
from memovi_search.domain.repositories import EmbeddingRepository
from memovi_search.domain.retrievers.retriever import RetrievalRequest
from memovi_search.domain.value_objects import EmbeddingVector


class SemanticRetriever:
    """Vector similarity retrieval over search-document embeddings."""

    def __init__(
        self,
        *,
        embedding_provider: EmbeddingProvider,
        embedding_repository: EmbeddingRepository,
    ) -> None:
        self._embedding_provider = embedding_provider
        self._embedding_repository = embedding_repository

    def retrieve(self, request: RetrievalRequest) -> list[SearchResult]:
        if not request.query.strip() or request.limit <= 0:
            return []

        query_vector = self._embed_query(request.query.strip())
        ranked = self._embedding_repository.similarity_search(
            query_vector,
            request.limit,
            workspace_id=request.workspace_id,
        )
        return [
            SearchResult(
                search_document=item.search_document,
                score=item.relevance_score,
            )
            for item in ranked
        ]

    def _embed_query(self, query: str) -> EmbeddingVector:
        vector = self._embedding_provider.embed(query)
        return EmbeddingVector(values=list(vector.values), dimensions=vector.dimensions)
