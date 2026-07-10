from dataclasses import dataclass
from datetime import datetime

from memovi_search.domain.entities import SearchDocument


@dataclass(frozen=True, slots=True)
class SearchDocumentDto:
    id: str
    knowledge_item_id: str
    document_id: str
    document_version_id: str
    searchable_text: str
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_search_document(cls, search_document: SearchDocument) -> SearchDocumentDto:
        return cls(
            id=search_document.id.value,
            knowledge_item_id=search_document.knowledge_item_id,
            document_id=search_document.document_id,
            document_version_id=search_document.document_version_id,
            searchable_text=search_document.searchable_text,
            created_at=search_document.created_at,
            updated_at=search_document.updated_at,
        )
