from memovi_search.domain.value_objects.embedding_vector import EmbeddingVector


class OllamaEmbeddingProvider:
    """Placeholder for Ollama embedding generation."""

    def embed(self, text: str) -> EmbeddingVector:
        raise NotImplementedError("Ollama embedding generation is not implemented yet.")

    def embed_many(self, texts: list[str]) -> list[EmbeddingVector]:
        raise NotImplementedError("Ollama embedding generation is not implemented yet.")
