from memovi_search.domain.value_objects.embedding_vector import EmbeddingVector


class OpenAIEmbeddingProvider:
    """Placeholder for OpenAI embedding generation."""

    @property
    def provider(self) -> str:
        return "openai"

    @property
    def model(self) -> str:
        return "text-embedding-3-small"

    def embed(self, text: str) -> EmbeddingVector:
        raise NotImplementedError("OpenAI embedding generation is not implemented yet.")

    def embed_many(self, texts: list[str]) -> list[EmbeddingVector]:
        raise NotImplementedError("OpenAI embedding generation is not implemented yet.")
