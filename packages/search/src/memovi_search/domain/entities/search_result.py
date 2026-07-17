from dataclasses import dataclass

from memovi_search.domain.entities.search_document import SearchDocument


@dataclass(frozen=True, slots=True)
class SearchResult:
    """A single ranked retrieval hit produced by a retriever or fusion step."""

    search_document: SearchDocument
    score: float
