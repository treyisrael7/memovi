from dataclasses import dataclass

from memovi_search.application.dto import SearchDocumentDto, SearchFilters, SearchResultDto
from memovi_search.application.services.retrieval_engine import (
    RetrievalEngine,
    RetrievalEngineRequest,
    RetrievalMode,
)


@dataclass(frozen=True, slots=True)
class RetrieveKnowledgeQuery:
    query: str
    limit: int
    offset: int = 0
    mode: RetrievalMode = RetrievalMode.HYBRID
    filters: SearchFilters | None = None


class RetrieveKnowledge:
    """Unified retrieval use case over keyword, semantic, and hybrid modes."""

    def __init__(self, *, retrieval_engine: RetrievalEngine) -> None:
        self._retrieval_engine = retrieval_engine

    def execute(self, query: RetrieveKnowledgeQuery) -> list[SearchResultDto]:
        results = self._retrieval_engine.retrieve(
            RetrievalEngineRequest(
                query=query.query,
                mode=query.mode,
                limit=query.limit,
                offset=query.offset,
                filters=query.filters,
            )
        )
        return [
            SearchResultDto.from_search_document_dto(
                search_document=SearchDocumentDto.from_search_document(
                    result.search_document,
                ),
                relevance_score=result.score,
            )
            for result in results
        ]
