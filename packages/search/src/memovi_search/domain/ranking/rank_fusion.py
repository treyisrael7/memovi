from collections import defaultdict

from memovi_search.domain.entities.search_document import SearchDocument
from memovi_search.domain.entities.search_result import SearchResult

DEFAULT_RRF_K = 60


class RankFusion:
    """Merges ranked retrieval lists with Reciprocal Rank Fusion (RRF)."""

    def __init__(self, *, k: int = DEFAULT_RRF_K) -> None:
        if k <= 0:
            raise ValueError("RRF k must be a positive integer.")
        self._k = k

    @property
    def k(self) -> int:
        return self._k

    def fuse(self, ranked_lists: list[list[SearchResult]]) -> list[SearchResult]:
        if not ranked_lists:
            return []

        non_empty = [ranked for ranked in ranked_lists if ranked]
        if not non_empty:
            return []
        if len(non_empty) == 1:
            return list(non_empty[0])

        scores: dict[str, float] = defaultdict(float)
        documents: dict[str, SearchDocument] = {}

        for ranked in non_empty:
            for rank, result in enumerate(ranked, start=1):
                document_id = result.search_document.id.value
                scores[document_id] += 1.0 / (self._k + rank)
                documents[document_id] = result.search_document

        fused = [
            SearchResult(search_document=documents[document_id], score=score)
            for document_id, score in scores.items()
        ]
        fused.sort(
            key=lambda item: (
                -item.score,
                item.search_document.created_at,
                item.search_document.id.value,
            ),
        )
        return fused
