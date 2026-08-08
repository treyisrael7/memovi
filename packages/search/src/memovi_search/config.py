from __future__ import annotations

import os
from dataclasses import dataclass
from enum import StrEnum

from memovi_search.application.exceptions import InvalidEmbeddingConfigError
from memovi_search.infrastructure.persistence.vector import EMBEDDING_VECTOR_DIMENSIONS


class EmbeddingProviderKind(StrEnum):
    """Supported embedding provider identifiers for configuration selection."""

    FAKE = "fake"
    OPENAI = "openai"
    OLLAMA = "ollama"
    SENTENCE_TRANSFORMER = "sentence_transformer"


DEFAULT_MODELS: dict[EmbeddingProviderKind, str] = {
    EmbeddingProviderKind.FAKE: "fake-embedding-v1",
    EmbeddingProviderKind.OPENAI: "text-embedding-3-small",
    EmbeddingProviderKind.OLLAMA: "all-minilm",
    EmbeddingProviderKind.SENTENCE_TRANSFORMER: "all-MiniLM-L6-v2",
}

DEFAULT_OLLAMA_ENDPOINT = "http://127.0.0.1:11434"


@dataclass(frozen=True, slots=True)
class SearchEmbeddingConfig:
    """Typed configuration for Search embedding provider selection.

    Dimensions must match the pgvector schema constant
    ``EMBEDDING_VECTOR_DIMENSIONS``. Changing dimensions requires a migration
    and full re-index.
    """

    provider: str = EmbeddingProviderKind.FAKE.value
    model: str | None = None
    dimensions: int = EMBEDDING_VECTOR_DIMENSIONS
    endpoint: str | None = None
    api_key: str | None = None
    timeout_seconds: float = 60.0

    def __post_init__(self) -> None:
        provider = self.provider.strip().lower()
        if not provider:
            raise InvalidEmbeddingConfigError("SEARCH_EMBEDDING_PROVIDER cannot be blank.")
        try:
            kind = EmbeddingProviderKind(provider)
        except ValueError as exc:
            supported = ", ".join(sorted(item.value for item in EmbeddingProviderKind))
            raise InvalidEmbeddingConfigError(
                f"Unsupported embedding provider '{provider}'. Supported: {supported}.",
            ) from exc
        object.__setattr__(self, "provider", kind.value)

        if self.dimensions != EMBEDDING_VECTOR_DIMENSIONS:
            raise InvalidEmbeddingConfigError(
                f"SEARCH_EMBEDDING_DIMENSIONS must be {EMBEDDING_VECTOR_DIMENSIONS} "
                f"to match pgvector storage (got {self.dimensions}). "
                "Change the schema constant and migrate before selecting a new size.",
            )
        if self.dimensions < 1:
            raise InvalidEmbeddingConfigError("dimensions must be at least 1.")

        if self.model is None:
            resolved_model = DEFAULT_MODELS[kind]
        else:
            resolved_model = self.model.strip()
        if not resolved_model:
            raise InvalidEmbeddingConfigError("SEARCH_EMBEDDING_MODEL cannot be blank.")
        object.__setattr__(self, "model", resolved_model)

        endpoint = self.endpoint.strip() if self.endpoint is not None else None
        if endpoint is not None and not endpoint:
            raise InvalidEmbeddingConfigError("SEARCH_EMBEDDING_ENDPOINT cannot be blank.")
        if kind == EmbeddingProviderKind.OLLAMA and endpoint is None:
            endpoint = DEFAULT_OLLAMA_ENDPOINT
        object.__setattr__(self, "endpoint", endpoint)

        api_key = self.api_key.strip() if self.api_key is not None else None
        if api_key is not None and not api_key:
            raise InvalidEmbeddingConfigError("Embedding API key cannot be blank.")
        if kind == EmbeddingProviderKind.OPENAI and not api_key:
            raise InvalidEmbeddingConfigError(
                "OPENAI_API_KEY (or SEARCH_EMBEDDING_API_KEY) is required for the "
                "openai embedding provider.",
            )
        object.__setattr__(self, "api_key", api_key)

        if self.timeout_seconds <= 0:
            raise InvalidEmbeddingConfigError("timeout_seconds must be positive.")

    @property
    def kind(self) -> EmbeddingProviderKind:
        return EmbeddingProviderKind(self.provider)

    @classmethod
    def from_env(cls) -> SearchEmbeddingConfig:
        """Load embedding provider selection from process environment variables.

        Recognized variables:
        - ``SEARCH_EMBEDDING_PROVIDER`` (default: ``fake``)
        - ``SEARCH_EMBEDDING_MODEL`` (optional override)
        - ``SEARCH_EMBEDDING_DIMENSIONS`` (must match pgvector schema)
        - ``SEARCH_EMBEDDING_ENDPOINT`` (Ollama base URL; optional OpenAI base URL)
        - ``SEARCH_EMBEDDING_API_KEY`` or ``OPENAI_API_KEY`` (OpenAI)
        - ``SEARCH_EMBEDDING_TIMEOUT_SECONDS`` (default: ``60``)
        """
        provider = os.environ.get(
            "SEARCH_EMBEDDING_PROVIDER",
            EmbeddingProviderKind.FAKE.value,
        )
        model = os.environ.get("SEARCH_EMBEDDING_MODEL")
        dimensions_raw = os.environ.get("SEARCH_EMBEDDING_DIMENSIONS")
        if dimensions_raw is None:
            dimensions = EMBEDDING_VECTOR_DIMENSIONS
        else:
            try:
                dimensions = int(dimensions_raw)
            except ValueError as exc:
                raise InvalidEmbeddingConfigError(
                    "SEARCH_EMBEDDING_DIMENSIONS must be an integer.",
                ) from exc
        endpoint = os.environ.get("SEARCH_EMBEDDING_ENDPOINT")
        api_key = os.environ.get("SEARCH_EMBEDDING_API_KEY") or os.environ.get("OPENAI_API_KEY")
        timeout_raw = os.environ.get("SEARCH_EMBEDDING_TIMEOUT_SECONDS", "60")
        try:
            timeout_seconds = float(timeout_raw)
        except ValueError as exc:
            raise InvalidEmbeddingConfigError(
                "SEARCH_EMBEDDING_TIMEOUT_SECONDS must be a number.",
            ) from exc
        return cls(
            provider=provider,
            model=model,
            dimensions=dimensions,
            endpoint=endpoint,
            api_key=api_key,
            timeout_seconds=timeout_seconds,
        )
