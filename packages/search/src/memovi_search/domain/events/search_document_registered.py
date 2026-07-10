from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class SearchDocumentRegistered:
    """Domain fact emitted when a knowledge item becomes searchable."""

    search_document_id: str
    knowledge_item_id: str
    document_id: str
    document_version_id: str
    occurred_at: datetime
