from __future__ import annotations

from typing import Any

from memovi_search.application.exceptions import (
    EmbeddingProviderError,
    EmbeddingProviderUnavailableError,
)
from memovi_search.domain.value_objects.embedding_vector import EmbeddingVector
from memovi_search.infrastructure.persistence.vector import EMBEDDING_VECTOR_DIMENSIONS


class SentenceTransformerEmbeddingProvider:
    """Local Sentence Transformers embedding adapter."""

    def __init__(
        self,
        *,
        model: str = "all-MiniLM-L6-v2",
        dimensions: int | None = None,
        encoder: Any | None = None,
    ) -> None:
        self._model = model.strip()
        self._dimensions = dimensions if dimensions is not None else EMBEDDING_VECTOR_DIMENSIONS
        self._encoder = encoder

    @property
    def provider(self) -> str:
        return "sentence_transformer"

    @property
    def model(self) -> str:
        return self._model

    def embed(self, text: str) -> EmbeddingVector:
        return self.embed_many([text])[0]

    def embed_many(self, texts: list[str]) -> list[EmbeddingVector]:
        if not texts:
            return []
        encoder = self._encoder or self._load_encoder()
        try:
            raw = encoder.encode(texts, normalize_embeddings=True)
        except Exception as exc:
            raise EmbeddingProviderError(
                f"Sentence Transformers embedding failed: {exc}",
            ) from exc

        try:
            rows = [list(map(float, row)) for row in raw]
        except (TypeError, ValueError) as exc:
            raise EmbeddingProviderError(
                "Sentence Transformers returned a non-numeric embedding matrix.",
            ) from exc

        if len(rows) != len(texts):
            raise EmbeddingProviderError(
                "Sentence Transformers batch size did not match input texts.",
            )
        return [_to_vector(values, self._dimensions) for values in rows]

    def _load_encoder(self) -> Any:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise EmbeddingProviderUnavailableError(
                "The sentence-transformers package is required for "
                "SentenceTransformerEmbeddingProvider. Install it before selecting "
                "SEARCH_EMBEDDING_PROVIDER=sentence_transformer.",
            ) from exc
        try:
            return SentenceTransformer(self._model)
        except Exception as exc:
            raise EmbeddingProviderUnavailableError(
                f"Failed to load Sentence Transformers model '{self._model}': {exc}",
            ) from exc


def _to_vector(values: list[float], expected_dimensions: int) -> EmbeddingVector:
    if len(values) != expected_dimensions:
        raise EmbeddingProviderError(
            f"Sentence Transformers embedding dimensions must be {expected_dimensions} "
            f"(got {len(values)}). Choose a model that matches "
            "SEARCH_EMBEDDING_DIMENSIONS / pgvector schema, or migrate the schema.",
        )
    return EmbeddingVector(values=values, dimensions=expected_dimensions)
