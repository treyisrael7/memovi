from dataclasses import dataclass
from datetime import datetime

from memovi_search.domain.entities import SearchDocument


@dataclass(frozen=True, slots=True)
class SearchDocumentDto:
    id: str
    document_id: str
    document_version_id: str
    chunk_id: str
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_search_document(cls, search_document: SearchDocument) -> SearchDocumentDto:
        return cls(
            id=search_document.id.value,
            document_id=search_document.document_id,
            document_version_id=search_document.document_version_id,
            chunk_id=search_document.chunk_id,
            created_at=search_document.created_at,
            updated_at=search_document.updated_at,
        )
