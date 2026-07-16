from dataclasses import dataclass

from memovi_search.domain.entities.search_document import SearchDocument


@dataclass(frozen=True, slots=True)
class RankedSearchDocument:
    """Search document matched by full-text retrieval with a relevance score."""

    search_document: SearchDocument
    relevance_score: float
