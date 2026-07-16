from memovi_search.application.exceptions import EmbeddingGenerationError
from memovi_search.domain.providers import EmbeddingProvider
from memovi_search.domain.value_objects import EmbeddingVector


class EmbeddingGenerationService:
    """Orchestrates provider-agnostic embedding generation."""

    def __init__(self, *, provider: EmbeddingProvider) -> None:
        self._provider = provider

    @property
    def provider(self) -> str:
        return self._provider.provider

    @property
    def model(self) -> str:
        return self._provider.model

    def generate(self, text: str) -> EmbeddingVector:
        return self._validate_vector(self._provider.embed(text))

    def generate_many(self, texts: list[str]) -> list[EmbeddingVector]:
        vectors = self._provider.embed_many(texts)
        if len(vectors) != len(texts):
            raise EmbeddingGenerationError(
                "Embedding provider must return one vector for each input text.",
            )
        return [self._validate_vector(vector) for vector in vectors]

    @staticmethod
    def _validate_vector(vector: EmbeddingVector) -> EmbeddingVector:
        if not isinstance(vector, EmbeddingVector):
            raise EmbeddingGenerationError(
                "Embedding provider must return EmbeddingVector instances.",
            )
        # Reconstruct to re-enforce value-object invariants at the application boundary.
        return EmbeddingVector(values=list(vector.values), dimensions=vector.dimensions)
