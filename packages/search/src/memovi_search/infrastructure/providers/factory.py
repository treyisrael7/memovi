from dataclasses import dataclass
from enum import StrEnum

from memovi_search.application.exceptions import UnknownEmbeddingProviderError
from memovi_search.domain.providers import EmbeddingProvider
from memovi_search.infrastructure.providers.ollama_embedding_provider import (
    OllamaEmbeddingProvider,
)
from memovi_search.infrastructure.providers.openai_embedding_provider import (
    OpenAIEmbeddingProvider,
)
from memovi_search.infrastructure.providers.sentence_transformer_embedding_provider import (
    SentenceTransformerEmbeddingProvider,
)


class EmbeddingProviderKind(StrEnum):
    """Supported embedding provider identifiers for configuration selection."""

    OPENAI = "openai"
    OLLAMA = "ollama"
    SENTENCE_TRANSFORMER = "sentence_transformer"


@dataclass(frozen=True, slots=True)
class EmbeddingProviderConfig:
    """Selects the active embedding provider without loading environment values."""

    kind: EmbeddingProviderKind = EmbeddingProviderKind.OPENAI


_PROVIDER_TYPES: dict[
    EmbeddingProviderKind,
    type[OpenAIEmbeddingProvider]
    | type[OllamaEmbeddingProvider]
    | type[SentenceTransformerEmbeddingProvider],
] = {
    EmbeddingProviderKind.OPENAI: OpenAIEmbeddingProvider,
    EmbeddingProviderKind.OLLAMA: OllamaEmbeddingProvider,
    EmbeddingProviderKind.SENTENCE_TRANSFORMER: SentenceTransformerEmbeddingProvider,
}


def build_embedding_provider(config: EmbeddingProviderConfig) -> EmbeddingProvider:
    """Construct the configured embedding provider placeholder."""

    provider_type = _PROVIDER_TYPES.get(config.kind)
    if provider_type is None:
        raise UnknownEmbeddingProviderError(
            f"Unsupported embedding provider '{config.kind}'.",
        )
    return provider_type()
