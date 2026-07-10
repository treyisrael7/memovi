from dataclasses import dataclass

from memovi_search.domain.exceptions import InvalidEmbeddingError
from memovi_search.domain.value_objects import EmbeddingId, SearchDocumentId


@dataclass(frozen=True, slots=True)
class Embedding:
    """Vector associated with one searchable document projection."""

    id: EmbeddingId
    search_document_id: SearchDocumentId
    provider: str
    model: str
    dimensions: int
    vector: tuple[float, ...]

    def __post_init__(self) -> None:
        if not self.provider.strip():
            raise InvalidEmbeddingError("Embedding provider is required.")
        if not self.model.strip():
            raise InvalidEmbeddingError("Embedding model is required.")
        if len(self.vector) == 0:
            raise InvalidEmbeddingError("Embedding vector cannot be empty.")
        if self.dimensions != len(self.vector):
            raise InvalidEmbeddingError("Embedding dimensions must match vector length.")
        object.__setattr__(self, "provider", self.provider.strip())
        object.__setattr__(self, "model", self.model.strip())

    @classmethod
    def create(
        cls,
        *,
        search_document_id: SearchDocumentId,
        provider: str,
        model: str,
        vector: list[float],
    ) -> Embedding:
        normalized_vector = tuple(vector)
        return cls(
            id=EmbeddingId.new(),
            search_document_id=search_document_id,
            provider=provider,
            model=model,
            dimensions=len(normalized_vector),
            vector=normalized_vector,
        )
