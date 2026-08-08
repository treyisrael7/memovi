from __future__ import annotations

from dataclasses import dataclass

from memovi_search.application.exceptions import (
    EmbeddingProviderUnavailableError,
    UnknownEmbeddingProviderError,
)
from memovi_search.config import EmbeddingProviderKind, SearchEmbeddingConfig
from memovi_search.domain.providers import EmbeddingProvider
from memovi_search.infrastructure.persistence.vector import EMBEDDING_VECTOR_DIMENSIONS
from memovi_search.infrastructure.providers.fake_embedding_provider import (
    FakeEmbeddingProvider,
)
from memovi_search.infrastructure.providers.ollama_embedding_provider import (
    OllamaEmbeddingProvider,
)
from memovi_search.infrastructure.providers.openai_embedding_provider import (
    OpenAIEmbeddingProvider,
)
from memovi_search.infrastructure.providers.sentence_transformer_embedding_provider import (
    SentenceTransformerEmbeddingProvider,
)


@dataclass(frozen=True, slots=True)
class EmbeddingProviderConfig:
    """Selects the active embedding provider without loading environment values.

    Prefer ``SearchEmbeddingConfig`` for env-backed composition. This type remains
    for tests and direct factory calls.
    """

    kind: EmbeddingProviderKind = EmbeddingProviderKind.OPENAI
    model: str | None = None
    dimensions: int | None = None
    endpoint: str | None = None
    api_key: str | None = None
    timeout_seconds: float = 60.0


def build_embedding_provider(
    config: SearchEmbeddingConfig | EmbeddingProviderConfig,
) -> EmbeddingProvider:
    """Construct the configured embedding provider.

    Fake is only returned when ``kind`` / ``provider`` is explicitly ``fake``.
    """
    if isinstance(config, SearchEmbeddingConfig):
        return _build_from_search_config(config)

    dimensions = config.dimensions if config.dimensions is not None else EMBEDDING_VECTOR_DIMENSIONS

    if config.kind == EmbeddingProviderKind.FAKE:
        return FakeEmbeddingProvider(dimensions=dimensions)
    if config.kind == EmbeddingProviderKind.OPENAI:
        if not config.api_key:
            raise EmbeddingProviderUnavailableError(
                "OpenAI API key is required for the openai embedding provider.",
            )
        return OpenAIEmbeddingProvider(
            api_key=config.api_key,
            model=config.model or "text-embedding-3-small",
            dimensions=dimensions,
            endpoint=config.endpoint,
            timeout_seconds=config.timeout_seconds,
        )
    if config.kind == EmbeddingProviderKind.OLLAMA:
        return OllamaEmbeddingProvider(
            model=config.model or "all-minilm",
            endpoint=config.endpoint or "http://127.0.0.1:11434",
            dimensions=dimensions,
            timeout_seconds=config.timeout_seconds,
        )
    if config.kind == EmbeddingProviderKind.SENTENCE_TRANSFORMER:
        return SentenceTransformerEmbeddingProvider(
            model=config.model or "all-MiniLM-L6-v2",
            dimensions=dimensions,
        )
    raise UnknownEmbeddingProviderError(
        f"Unsupported embedding provider '{config.kind}'.",
    )


def _build_from_search_config(config: SearchEmbeddingConfig) -> EmbeddingProvider:
    return build_embedding_provider(
        EmbeddingProviderConfig(
            kind=config.kind,
            model=config.model,
            dimensions=config.dimensions,
            endpoint=config.endpoint,
            api_key=config.api_key,
            timeout_seconds=config.timeout_seconds,
        ),
    )
