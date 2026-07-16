from dataclasses import dataclass

from memovi_search.application.dto.search_document_dto import SearchDocumentDto


@dataclass(frozen=True, slots=True)
class SearchResultDto:
    search_document_id: str
    knowledge_item_id: str
    document_id: str
    relevance_score: float
    searchable_text: str

    @classmethod
    def from_search_document_dto(
        cls,
        *,
        search_document: SearchDocumentDto,
        relevance_score: float,
    ) -> SearchResultDto:
        return cls(
            search_document_id=search_document.id,
            knowledge_item_id=search_document.knowledge_item_id,
            document_id=search_document.document_id,
            relevance_score=relevance_score,
            searchable_text=search_document.searchable_text,
        )
