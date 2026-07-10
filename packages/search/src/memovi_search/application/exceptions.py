class SearchApplicationError(Exception):
    """Base exception for search use-case failures."""


class SearchDocumentNotFoundError(SearchApplicationError):
    """Raised when a requested search document does not exist."""


class EmbeddingNotFoundError(SearchApplicationError):
    """Raised when a requested embedding does not exist."""
