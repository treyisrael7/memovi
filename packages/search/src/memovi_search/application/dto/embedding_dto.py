from dataclasses import dataclass
from datetime import datetime

from memovi_search.domain.entities import Embedding


@dataclass(frozen=True, slots=True)
class EmbeddingDto:
    id: str
    search_document_id: str
    model_id: str
    dimensions: int
    created_at: datetime

    @classmethod
    def from_embedding(cls, embedding: Embedding) -> EmbeddingDto:
        return cls(
            id=embedding.id.value,
            search_document_id=embedding.search_document_id.value,
            model_id=embedding.model_id,
            dimensions=embedding.dimensions,
            created_at=embedding.created_at,
        )
