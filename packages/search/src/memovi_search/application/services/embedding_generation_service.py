from memovi_observability import get_metrics_recorder, timed_operation

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
        with timed_operation(
            "embedding.provider",
            metric_name="memovi.embedding.provider",
            attributes={
                "operation": "embedding.provider",
                "provider": self.provider,
                "model": self.model,
            },
        ):
            try:
                vector = self._validate_vector(self._provider.embed(text))
            except Exception:
                get_metrics_recorder().increment(
                    "memovi.embedding.provider.failures",
                    tags={"provider": self.provider, "model": self.model},
                )
                raise
        get_metrics_recorder().increment(
            "memovi.embedding.provider.success",
            tags={
                "provider": self.provider,
                "model": self.model,
                "dimensions": str(vector.dimensions),
            },
        )
        return vector

    def generate_many(self, texts: list[str]) -> list[EmbeddingVector]:
        with timed_operation(
            "embedding.provider.batch",
            metric_name="memovi.embedding.provider.batch",
            attributes={
                "operation": "embedding.provider.batch",
                "provider": self.provider,
                "model": self.model,
                "batch_size": len(texts),
            },
        ):
            try:
                vectors = self._provider.embed_many(texts)
            except Exception:
                get_metrics_recorder().increment(
                    "memovi.embedding.provider.failures",
                    tags={"provider": self.provider, "model": self.model},
                )
                raise
        if len(vectors) != len(texts):
            raise EmbeddingGenerationError(
                "Embedding provider must return one vector for each input text.",
            )
        validated = [self._validate_vector(vector) for vector in vectors]
        if validated:
            get_metrics_recorder().increment(
                "memovi.embedding.provider.success",
                tags={
                    "provider": self.provider,
                    "model": self.model,
                    "dimensions": str(validated[0].dimensions),
                },
            )
        return validated

    @staticmethod
    def _validate_vector(vector: EmbeddingVector) -> EmbeddingVector:
        if not isinstance(vector, EmbeddingVector):
            raise EmbeddingGenerationError(
                "Embedding provider must return EmbeddingVector instances.",
            )
        # Reconstruct to re-enforce value-object invariants at the application boundary.
        return EmbeddingVector(values=list(vector.values), dimensions=vector.dimensions)
