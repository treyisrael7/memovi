from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class SearchDocumentRegistered:
    """Domain fact emitted when a chunk becomes searchable."""

    search_document_id: str
    document_id: str
    document_version_id: str
    chunk_id: str
    occurred_at: datetime
