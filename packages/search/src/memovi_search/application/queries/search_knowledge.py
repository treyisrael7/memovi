from dataclasses import dataclass

from memovi_search.application.dto import SearchDocumentDto, SearchResultDto
from memovi_search.domain.repositories import SearchRepository


@dataclass(frozen=True, slots=True)
class SearchKnowledgeQuery:
    query: str
    limit: int
    offset: int


class SearchKnowledge:
    """Returns ranked full-text search matches for indexed knowledge."""

    def __init__(self, *, search_repository: SearchRepository) -> None:
        self._search_repository = search_repository

    def execute(self, query: SearchKnowledgeQuery) -> list[SearchResultDto]:
        normalized_query = query.query.strip()
        if not normalized_query:
            return []

        ranked_documents = self._search_repository.search(
            normalized_query,
            query.limit,
            query.offset,
        )
        return [
            SearchResultDto.from_search_document_dto(
                search_document=SearchDocumentDto.from_search_document(
                    ranked.search_document,
                ),
                relevance_score=ranked.relevance_score,
            )
            for ranked in ranked_documents
        ]
