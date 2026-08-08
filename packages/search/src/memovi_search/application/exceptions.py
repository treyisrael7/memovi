class SearchApplicationError(Exception):
    """Base exception for search use-case failures."""


class SearchDocumentNotFoundError(SearchApplicationError):
    """Raised when a requested search document does not exist."""


class EmbeddingNotFoundError(SearchApplicationError):
    """Raised when a requested embedding does not exist."""


class EmbeddingGenerationError(SearchApplicationError):
    """Raised when embedding generation fails application-level validation."""


class UnknownEmbeddingProviderError(SearchApplicationError):
    """Raised when configuration selects an unsupported embedding provider."""


class InvalidEmbeddingConfigError(SearchApplicationError):
    """Raised when embedding provider configuration is invalid."""


class EmbeddingProviderError(SearchApplicationError):
    """Raised when an embedding provider call fails."""


class EmbeddingProviderUnavailableError(EmbeddingProviderError):
    """Raised when an embedding provider or its dependencies are unavailable."""
