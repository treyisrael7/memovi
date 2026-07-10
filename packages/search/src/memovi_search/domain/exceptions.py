class SearchDomainError(Exception):
    """Base exception for search domain invariant failures."""


class InvalidSearchDocumentIdError(SearchDomainError):
    """Raised when a search document identifier is malformed."""


class InvalidEmbeddingIdError(SearchDomainError):
    """Raised when an embedding identifier is malformed."""


class InvalidSearchDocumentError(SearchDomainError):
    """Raised when a search document violates its invariants."""


class InvalidEmbeddingError(SearchDomainError):
    """Raised when an embedding violates its invariants."""


class InvalidDocumentReferenceError(SearchDomainError):
    """Raised when a document reference on a search document is invalid."""


class InvalidChunkReferenceError(SearchDomainError):
    """Raised when a chunk reference on a search document is invalid."""
