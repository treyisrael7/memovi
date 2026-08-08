from __future__ import annotations

from typing import Any

from memovi_search.application.exceptions import (
    EmbeddingProviderError,
    EmbeddingProviderUnavailableError,
)
from memovi_search.domain.value_objects.embedding_vector import EmbeddingVector
from memovi_search.infrastructure.persistence.vector import EMBEDDING_VECTOR_DIMENSIONS


class OllamaEmbeddingProvider:
    """Ollama embeddings adapter via the local HTTP ``/api/embeddings`` API."""

    def __init__(
        self,
        *,
        model: str = "all-minilm",
        endpoint: str = "http://127.0.0.1:11434",
        dimensions: int | None = None,
        timeout_seconds: float = 60.0,
        http_client: Any | None = None,
    ) -> None:
        self._model = model.strip()
        self._endpoint = endpoint.rstrip("/")
        self._dimensions = dimensions if dimensions is not None else EMBEDDING_VECTOR_DIMENSIONS
        self._timeout_seconds = timeout_seconds
        self._http_client = http_client

    @property
    def provider(self) -> str:
        return "ollama"

    @property
    def model(self) -> str:
        return self._model

    def embed(self, text: str) -> EmbeddingVector:
        payload = self._request_embedding(text)
        return _to_vector(payload, self._dimensions)

    def embed_many(self, texts: list[str]) -> list[EmbeddingVector]:
        return [self.embed(text) for text in texts]

    def _request_embedding(self, text: str) -> list[float]:
        client = self._http_client or _build_httpx_client(self._timeout_seconds)
        url = f"{self._endpoint}/api/embeddings"
        try:
            response = client.post(url, json={"model": self._model, "prompt": text})
            response.raise_for_status()
            payload = response.json()
        except Exception as exc:
            raise _translate_http_error(exc, endpoint=self._endpoint) from exc

        embedding = payload.get("embedding") if isinstance(payload, dict) else None
        if not isinstance(embedding, list) or not embedding:
            raise EmbeddingProviderError(
                "Ollama embedding response did not include an embedding vector.",
            )
        try:
            return [float(value) for value in embedding]
        except (TypeError, ValueError) as exc:
            raise EmbeddingProviderError(
                "Ollama embedding response contained non-numeric values.",
            ) from exc


def _build_httpx_client(timeout_seconds: float) -> Any:
    try:
        import httpx
    except ImportError as exc:
        raise EmbeddingProviderUnavailableError(
            "The httpx package is required for OllamaEmbeddingProvider.",
        ) from exc
    return httpx.Client(timeout=timeout_seconds)


def _to_vector(values: list[float], expected_dimensions: int) -> EmbeddingVector:
    if len(values) != expected_dimensions:
        raise EmbeddingProviderError(
            f"Ollama embedding dimensions must be {expected_dimensions} "
            f"(got {len(values)}). Choose a model that matches "
            "SEARCH_EMBEDDING_DIMENSIONS / pgvector schema, or migrate the schema.",
        )
    return EmbeddingVector(values=values, dimensions=expected_dimensions)


def _translate_http_error(exc: Exception, *, endpoint: str) -> EmbeddingProviderError:
    name = type(exc).__name__
    message = str(exc)
    if "Connect" in name or "connection" in message.lower():
        return EmbeddingProviderUnavailableError(
            f"Ollama embedding endpoint could not be reached at {endpoint}: {message}",
        )
    if "Timeout" in name or "timeout" in message.lower():
        return EmbeddingProviderError(f"Ollama embedding request timed out: {message}")
    return EmbeddingProviderError(f"Ollama embedding request failed: {message}")
