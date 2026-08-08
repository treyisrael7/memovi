from __future__ import annotations

from typing import Any, Protocol

from memovi_search.application.exceptions import (
    EmbeddingProviderError,
    EmbeddingProviderUnavailableError,
)
from memovi_search.domain.value_objects.embedding_vector import EmbeddingVector
from memovi_search.infrastructure.persistence.vector import EMBEDDING_VECTOR_DIMENSIONS


class SupportsOpenAIEmbeddings(Protocol):
    """Minimal client surface used by OpenAIEmbeddingProvider."""

    @property
    def embeddings(self) -> Any: ...


class OpenAIEmbeddingProvider:
    """OpenAI embeddings adapter (text-embedding-3-* and compatible endpoints)."""

    def __init__(
        self,
        *,
        api_key: str,
        model: str = "text-embedding-3-small",
        dimensions: int | None = None,
        endpoint: str | None = None,
        timeout_seconds: float = 60.0,
        client: SupportsOpenAIEmbeddings | None = None,
    ) -> None:
        self._model = model.strip()
        self._dimensions = dimensions if dimensions is not None else EMBEDDING_VECTOR_DIMENSIONS
        self._client = client or _build_openai_client(
            api_key=api_key,
            timeout_seconds=timeout_seconds,
            endpoint=endpoint,
        )

    @property
    def provider(self) -> str:
        return "openai"

    @property
    def model(self) -> str:
        return self._model

    def embed(self, text: str) -> EmbeddingVector:
        return self.embed_many([text])[0]

    def embed_many(self, texts: list[str]) -> list[EmbeddingVector]:
        if not texts:
            return []
        try:
            response = self._client.embeddings.create(
                model=self._model,
                input=texts,
                dimensions=self._dimensions,
            )
        except Exception as exc:
            raise _translate_openai_error(exc) from exc

        try:
            items = sorted(response.data, key=lambda item: item.index)
            vectors = [list(item.embedding) for item in items]
        except (AttributeError, TypeError) as exc:
            raise EmbeddingProviderError(
                "OpenAI embedding response could not be parsed.",
            ) from exc

        if len(vectors) != len(texts):
            raise EmbeddingProviderError(
                "OpenAI embedding response size did not match input batch size.",
            )
        return [_to_vector(values, self._dimensions) for values in vectors]


def _build_openai_client(
    *,
    api_key: str,
    timeout_seconds: float,
    endpoint: str | None,
) -> SupportsOpenAIEmbeddings:
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise EmbeddingProviderUnavailableError(
            "The openai package is required for OpenAIEmbeddingProvider.",
        ) from exc

    kwargs: dict[str, Any] = {
        "api_key": api_key,
        "timeout": timeout_seconds,
    }
    if endpoint is not None:
        kwargs["base_url"] = endpoint
    return OpenAI(**kwargs)


def _to_vector(values: list[float], expected_dimensions: int) -> EmbeddingVector:
    if len(values) != expected_dimensions:
        raise EmbeddingProviderError(
            f"OpenAI embedding dimensions must be {expected_dimensions} "
            f"(got {len(values)}).",
        )
    return EmbeddingVector(values=values, dimensions=expected_dimensions)


def _translate_openai_error(exc: Exception) -> EmbeddingProviderError:
    name = type(exc).__name__
    message = str(exc)
    if "Timeout" in name or "timeout" in message.lower():
        return EmbeddingProviderError(f"OpenAI embedding request timed out: {message}")
    if "Authentication" in name or "auth" in message.lower() or "api key" in message.lower():
        return EmbeddingProviderUnavailableError(
            "OpenAI embedding authentication failed. Check OPENAI_API_KEY.",
        )
    if "Connect" in name or "connection" in message.lower():
        return EmbeddingProviderUnavailableError(
            f"OpenAI embedding endpoint could not be reached: {message}",
        )
    return EmbeddingProviderError(f"OpenAI embedding request failed: {message}")
