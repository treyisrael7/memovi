from memovi_search.domain.value_objects.embedding_vector import EmbeddingVector
from memovi_search.infrastructure.persistence.vector import EMBEDDING_VECTOR_DIMENSIONS


class FakeEmbeddingProvider:
    """Deterministic local embedding provider for tests and explicit local wiring.

    Uses a hashed bag-of-words projection so texts with overlapping tokens are
    closer in cosine space than unrelated texts, while remaining fully local.
    Never selected implicitly by the production composition root — configure
    ``SEARCH_EMBEDDING_PROVIDER=fake`` to use it.
    """

    def __init__(self, *, dimensions: int | None = None) -> None:
        self._dimensions = dimensions if dimensions is not None else EMBEDDING_VECTOR_DIMENSIONS

    @property
    def provider(self) -> str:
        return "fake"

    @property
    def model(self) -> str:
        return "fake-embedding-v1"

    def embed(self, text: str) -> EmbeddingVector:
        tokens = [token for token in text.lower().split() if token]
        values = [0.0] * self._dimensions
        if not tokens:
            values = [1.0 / self._dimensions] * self._dimensions
        else:
            for token in tokens:
                bucket = sum(ord(character) for character in token) % self._dimensions
                values[bucket] += 1.0
            norm = sum(value * value for value in values) ** 0.5 or 1.0
            values = [value / norm for value in values]
        return EmbeddingVector(values=values, dimensions=self._dimensions)

    def embed_many(self, texts: list[str]) -> list[EmbeddingVector]:
        return [self.embed(text) for text in texts]
