from memovi_search.domain.value_objects.embedding_vector import EmbeddingVector


class SentenceTransformerEmbeddingProvider:
    """Placeholder for Sentence Transformer embedding generation."""

    @property
    def provider(self) -> str:
        return "sentence_transformer"

    @property
    def model(self) -> str:
        return "all-MiniLM-L6-v2"

    def embed(self, text: str) -> EmbeddingVector:
        raise NotImplementedError(
            "Sentence Transformer embedding generation is not implemented yet.",
        )

    def embed_many(self, texts: list[str]) -> list[EmbeddingVector]:
        raise NotImplementedError(
            "Sentence Transformer embedding generation is not implemented yet.",
        )
