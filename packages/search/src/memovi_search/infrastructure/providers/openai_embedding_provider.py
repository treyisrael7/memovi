from memovi_search.domain.value_objects.embedding_vector import EmbeddingVector


class OpenAIEmbeddingProvider:
    """Placeholder for OpenAI embedding generation."""

    def embed(self, text: str) -> EmbeddingVector:
        raise NotImplementedError("OpenAI embedding generation is not implemented yet.")

    def embed_many(self, texts: list[str]) -> list[EmbeddingVector]:
        raise NotImplementedError("OpenAI embedding generation is not implemented yet.")
