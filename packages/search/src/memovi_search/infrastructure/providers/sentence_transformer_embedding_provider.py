from memovi_search.domain.value_objects.embedding_vector import EmbeddingVector


class SentenceTransformerEmbeddingProvider:
    """Placeholder for Sentence Transformer embedding generation."""

    def embed(self, text: str) -> EmbeddingVector:
        raise NotImplementedError(
            "Sentence Transformer embedding generation is not implemented yet.",
        )

    def embed_many(self, texts: list[str]) -> list[EmbeddingVector]:
        raise NotImplementedError(
            "Sentence Transformer embedding generation is not implemented yet.",
        )
