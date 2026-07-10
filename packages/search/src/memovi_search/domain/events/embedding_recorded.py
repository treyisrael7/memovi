from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class EmbeddingRecorded:
    """Domain fact emitted when an embedding is stored for a search document."""

    embedding_id: str
    search_document_id: str
    provider: str
    model: str
    dimensions: int
    occurred_at: datetime
