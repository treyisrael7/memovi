from dataclasses import dataclass
from datetime import datetime

from documents.domain.entities import Document


@dataclass(frozen=True, slots=True)
class DocumentDto:
    id: str
    name: str
    mime_type: str
    source_type: str
    created_at: datetime

    @classmethod
    def from_document(cls, document: Document) -> DocumentDto:
        return cls(
            id=document.id.value,
            name=document.name.value,
            mime_type=document.mime_type.value,
            source_type=document.source_type.value,
            created_at=document.created_at,
        )
