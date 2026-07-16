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
