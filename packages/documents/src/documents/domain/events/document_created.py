from dataclasses import dataclass
from datetime import datetime

from documents.domain.value_objects import DocumentId


@dataclass(frozen=True, slots=True)
class DocumentCreated:
    """Domain fact emitted after a normalized document is registered."""

    document_id: DocumentId
    occurred_at: datetime
