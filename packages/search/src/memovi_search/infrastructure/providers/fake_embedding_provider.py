from memovi_search.domain.value_objects.embedding_vector import EmbeddingVector


class FakeEmbeddingProvider:
    """Deterministic local embedding provider for tests and development wiring."""

    @property
    def provider(self) -> str:
        return "fake"

    @property
    def model(self) -> str:
        return "fake-embedding-v1"

    def embed(self, text: str) -> EmbeddingVector:
        seed = sum(ord(character) for character in text) or 1
        values = [((seed * factor) % 1000) / 1000.0 for factor in (3, 5, 7, 11)]
        return EmbeddingVector(values=values, dimensions=len(values))

    def embed_many(self, texts: list[str]) -> list[EmbeddingVector]:
        return [self.embed(text) for text in texts]
