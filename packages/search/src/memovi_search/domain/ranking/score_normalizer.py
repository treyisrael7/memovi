from memovi_search.domain.entities.search_result import SearchResult


class ScoreNormalizer:
    """Min-max normalizes retrieval scores into the unit interval for presentation."""

    def normalize(self, results: list[SearchResult]) -> list[SearchResult]:
        if not results:
            return []
        if len(results) == 1:
            return [
                SearchResult(
                    search_document=results[0].search_document,
                    score=1.0,
                )
            ]

        scores = [result.score for result in results]
        minimum = min(scores)
        maximum = max(scores)
        span = maximum - minimum
        if span == 0:
            return [
                SearchResult(search_document=result.search_document, score=1.0)
                for result in results
            ]

        return [
            SearchResult(
                search_document=result.search_document,
                score=(result.score - minimum) / span,
            )
            for result in results
        ]
