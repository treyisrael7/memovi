"""Composition-root wiring for Search embedding providers."""

from __future__ import annotations

import logging

from fastapi import FastAPI
from memovi_search.application.exceptions import (
    EmbeddingProviderError,
    InvalidEmbeddingConfigError,
)
from memovi_search.config import SearchEmbeddingConfig
from memovi_search.domain.providers import EmbeddingProvider
from memovi_search.infrastructure.providers import build_embedding_provider

from api.bootstrap import LOGGER_NAME

LOGGER = logging.getLogger(LOGGER_NAME)


def load_embedding_config() -> SearchEmbeddingConfig:
    """Fail fast on invalid embedding configuration."""
    return SearchEmbeddingConfig.from_env()


def create_embedding_provider(
    config: SearchEmbeddingConfig | None = None,
    *,
    probe: bool = True,
) -> tuple[SearchEmbeddingConfig, EmbeddingProvider]:
    """Build the configured provider and optionally probe it at startup."""
    resolved = config or load_embedding_config()
    provider = build_embedding_provider(resolved)
    if probe:
        probe_embedding_provider(provider, config=resolved)
    return resolved, provider


def probe_embedding_provider(
    provider: EmbeddingProvider,
    *,
    config: SearchEmbeddingConfig,
) -> None:
    """Fail fast when the selected provider cannot produce a vector."""
    try:
        vector = provider.embed("memovi-embedding-startup-probe")
    except EmbeddingProviderError:
        raise
    except Exception as exc:
        raise EmbeddingProviderError(
            f"Embedding provider '{config.provider}/{config.model}' failed startup probe: {exc}",
        ) from exc
    if vector.dimensions != config.dimensions:
        raise InvalidEmbeddingConfigError(
            f"Embedding provider returned {vector.dimensions} dimensions; "
            f"expected {config.dimensions}.",
        )
    LOGGER.info(
        "Embedding provider ready: %s/%s (%s dimensions)",
        provider.provider,
        provider.model,
        vector.dimensions,
    )


def configure_embedding_provider(
    app: FastAPI,
    *,
    config: SearchEmbeddingConfig | None = None,
    provider: EmbeddingProvider | None = None,
    probe: bool = True,
) -> EmbeddingProvider:
    """Attach the embedding provider to application state for DI and readiness."""
    if provider is None:
        resolved, built = create_embedding_provider(config, probe=probe)
    else:
        resolved = config or getattr(app.state, "embedding_config", None) or load_embedding_config()
        built = provider
        if probe:
            probe_embedding_provider(built, config=resolved)
    app.state.embedding_config = resolved
    app.state.embedding_provider = built
    return built
