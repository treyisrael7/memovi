from typing import Protocol, runtime_checkable

from memovi_search.domain.value_objects.embedding_vector import EmbeddingVector


@runtime_checkable
class EmbeddingProvider(Protocol):
    """Generates embedding vectors without exposing provider-specific details."""

    def embed(self, text: str) -> EmbeddingVector:
        raise NotImplementedError

    def embed_many(self, texts: list[str]) -> list[EmbeddingVector]:
        raise NotImplementedError
