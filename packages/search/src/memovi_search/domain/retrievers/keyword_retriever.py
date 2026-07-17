from memovi_search.domain.entities.search_result import SearchResult
from memovi_search.domain.repositories import SearchRepository
from memovi_search.domain.retrievers.retriever import RetrievalRequest


class KeywordRetriever:
    """Full-text retrieval over searchable document projections."""

    def __init__(self, *, search_repository: SearchRepository) -> None:
        self._search_repository = search_repository

    def retrieve(self, request: RetrievalRequest) -> list[SearchResult]:
        if not request.query.strip() or request.limit <= 0:
            return []

        ranked = self._search_repository.search(
            request.query.strip(),
            request.limit,
            0,
        )
        return [
            SearchResult(
                search_document=item.search_document,
                score=item.relevance_score,
            )
            for item in ranked
        ]
