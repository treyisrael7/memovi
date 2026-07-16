from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class EmbeddingGenerated:
    """Domain fact emitted when an embedding is generated for a search document."""

    embedding_id: str
    search_document_id: str
    provider: str
    model: str
    dimensions: int
    generated_at: datetime
