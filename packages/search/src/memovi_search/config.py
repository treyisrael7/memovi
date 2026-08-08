from __future__ import annotations

import os
from dataclasses import dataclass

from memovi_config.exceptions import ConfigurationError
from memovi_config.settings.embeddings import (
    DEFAULT_MODELS,
    DEFAULT_OLLAMA_ENDPOINT,
    EmbeddingsSettings,
)
from memovi_config.settings.embeddings import (
    EMBEDDING_VECTOR_DIMENSIONS as CONFIG_EMBEDDING_DIMENSIONS,
)
from memovi_config.settings.embeddings import (
    EmbeddingProviderKind as EmbeddingProviderKind,
)

from memovi_search.application.exceptions import InvalidEmbeddingConfigError
from memovi_search.infrastructure.persistence.vector import EMBEDDING_VECTOR_DIMENSIONS

assert (
    CONFIG_EMBEDDING_DIMENSIONS == EMBEDDING_VECTOR_DIMENSIONS
), "memovi_config embedding dimensions must match pgvector schema constant"


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

        resolved_model = DEFAULT_MODELS[kind] if self.model is None else self.model.strip()
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

        Environment parsing is owned by ``memovi_config.EmbeddingsSettings``.
        """
        try:
            emb = EmbeddingsSettings.from_environ(os.environ)
        except ConfigurationError as exc:
            raise InvalidEmbeddingConfigError(str(exc)) from exc
        return cls(
            provider=emb.provider,
            model=emb.model,
            dimensions=emb.dimensions,
            endpoint=emb.endpoint,
            api_key=emb.api_key.get_secret_value() if emb.api_key is not None else None,
            timeout_seconds=emb.timeout_seconds,
        )
