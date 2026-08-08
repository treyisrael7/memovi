"""Embedding provider process settings."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from memovi_config.env import Environ, get_float, get_int, get_secret, get_str, require_http_url
from memovi_config.exceptions import ConfigurationError
from memovi_config.secrets import SecretValue

# Must match packages/search pgvector column size (EMBEDDING_VECTOR_DIMENSIONS).
EMBEDDING_VECTOR_DIMENSIONS = 384


class EmbeddingProviderKind(StrEnum):
    """Supported embedding provider identifiers."""

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
class EmbeddingsSettings:
    """Typed configuration for embedding provider selection."""

    provider: str = EmbeddingProviderKind.FAKE.value
    model: str | None = None
    dimensions: int = EMBEDDING_VECTOR_DIMENSIONS
    endpoint: str | None = None
    api_key: SecretValue | None = None
    timeout_seconds: float = 60.0

    def __post_init__(self) -> None:
        provider = self.provider.strip().lower()
        if not provider:
            raise ConfigurationError("SEARCH_EMBEDDING_PROVIDER cannot be blank.")
        try:
            kind = EmbeddingProviderKind(provider)
        except ValueError as exc:
            supported = ", ".join(sorted(item.value for item in EmbeddingProviderKind))
            raise ConfigurationError(
                f"Unsupported embedding provider '{provider}'. Supported: {supported}.",
            ) from exc
        object.__setattr__(self, "provider", kind.value)

        if self.dimensions != EMBEDDING_VECTOR_DIMENSIONS:
            raise ConfigurationError(
                f"SEARCH_EMBEDDING_DIMENSIONS must be {EMBEDDING_VECTOR_DIMENSIONS} "
                f"to match pgvector storage (got {self.dimensions}). "
                "Change the schema constant and migrate before selecting a new size.",
            )
        if self.dimensions < 1:
            raise ConfigurationError("SEARCH_EMBEDDING_DIMENSIONS must be at least 1.")

        resolved_model = DEFAULT_MODELS[kind] if self.model is None else self.model.strip()
        if not resolved_model:
            raise ConfigurationError("SEARCH_EMBEDDING_MODEL cannot be blank.")
        object.__setattr__(self, "model", resolved_model)

        endpoint = self.endpoint.strip() if self.endpoint is not None else None
        if endpoint is not None and not endpoint:
            raise ConfigurationError("SEARCH_EMBEDDING_ENDPOINT cannot be blank.")
        if endpoint is not None:
            require_http_url("SEARCH_EMBEDDING_ENDPOINT", endpoint)
        if kind == EmbeddingProviderKind.OLLAMA and endpoint is None:
            endpoint = DEFAULT_OLLAMA_ENDPOINT
        object.__setattr__(self, "endpoint", endpoint)

        if self.api_key is not None and not self.api_key.get_secret_value().strip():
            raise ConfigurationError("Embedding API key cannot be blank.")
        if kind == EmbeddingProviderKind.OPENAI and (
            self.api_key is None or not self.api_key.get_secret_value().strip()
        ):
            raise ConfigurationError(
                "OPENAI_API_KEY (or SEARCH_EMBEDDING_API_KEY) is required for the "
                "openai embedding provider.",
            )

        if self.timeout_seconds <= 0:
            raise ConfigurationError("SEARCH_EMBEDDING_TIMEOUT_SECONDS must be positive.")

    @property
    def kind(self) -> EmbeddingProviderKind:
        return EmbeddingProviderKind(self.provider)

    def __repr__(self) -> str:
        return (
            "EmbeddingsSettings("
            f"provider={self.provider!r}, "
            f"model={self.model!r}, "
            f"dimensions={self.dimensions!r}, "
            f"endpoint={self.endpoint!r}, "
            f"api_key={'SecretValue(***)' if self.api_key else None}, "
            f"timeout_seconds={self.timeout_seconds!r})"
        )

    @classmethod
    def from_environ(cls, environ: Environ) -> EmbeddingsSettings:
        provider = get_str(
            environ,
            "SEARCH_EMBEDDING_PROVIDER",
            default=EmbeddingProviderKind.FAKE.value,
        ) or EmbeddingProviderKind.FAKE.value
        model = get_str(environ, "SEARCH_EMBEDDING_MODEL", default=None)
        dimensions = get_int(
            environ,
            "SEARCH_EMBEDDING_DIMENSIONS",
            default=EMBEDDING_VECTOR_DIMENSIONS,
            minimum=1,
        )
        endpoint = get_str(environ, "SEARCH_EMBEDDING_ENDPOINT", default=None)
        api_key = get_secret(environ, "SEARCH_EMBEDDING_API_KEY", default=None)
        if api_key is None:
            api_key = get_secret(environ, "OPENAI_API_KEY", default=None)
        timeout_seconds = get_float(
            environ,
            "SEARCH_EMBEDDING_TIMEOUT_SECONDS",
            default=60.0,
            minimum=0.0,
        )
        return cls(
            provider=provider,
            model=model,
            dimensions=dimensions,
            endpoint=endpoint,
            api_key=api_key,
            timeout_seconds=timeout_seconds,
        )
