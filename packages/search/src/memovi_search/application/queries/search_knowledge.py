from dataclasses import dataclass

from memovi_search.application.dto import SearchDocumentDto, SearchFilters, SearchResultDto
from memovi_search.domain.repositories import SearchRepository


@dataclass(frozen=True, slots=True)
class SearchKnowledgeQuery:
    query: str
    limit: int
    offset: int
    filters: SearchFilters | None = None


class SearchKnowledge:
    """Returns ranked full-text search matches for indexed knowledge."""

    def __init__(self, *, search_repository: SearchRepository) -> None:
        self._search_repository = search_repository

    def execute(self, query: SearchKnowledgeQuery) -> list[SearchResultDto]:
        normalized_query = query.query.strip()
        if not normalized_query:
            return []

        filters = query.filters or SearchFilters()
        ranked_documents = self._search_repository.search(
            normalized_query,
            query.limit,
            query.offset,
            document_id=filters.document_id,
            document_version_id=filters.document_version_id,
            source_type=filters.source_type,
            mime_type=filters.mime_type,
            created_after=filters.created_after,
            created_before=filters.created_before,
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
