from dataclasses import dataclass

from memovi_search.domain.entities import Embedding


@dataclass(frozen=True, slots=True)
class EmbeddingDto:
    id: str
    search_document_id: str
    provider: str
    model: str
    dimensions: int
    vector: list[float]

    @classmethod
    def from_embedding(cls, embedding: Embedding) -> EmbeddingDto:
        return cls(
            id=embedding.id.value,
            search_document_id=embedding.search_document_id.value,
            provider=embedding.provider,
            model=embedding.model,
            dimensions=embedding.dimensions,
            vector=list(embedding.vector),
        )
