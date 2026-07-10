class MemoryDomainError(Exception):
    """Base exception for memory domain invariant failures."""


class InvalidKnowledgeItemIdError(MemoryDomainError):
    """Raised when a knowledge item identifier is malformed."""


class InvalidChunkIdError(MemoryDomainError):
    """Raised when a chunk identifier is malformed."""


class InvalidChunkIndexError(MemoryDomainError):
    """Raised when a chunk index violates domain constraints."""


class InvalidKnowledgeItemError(MemoryDomainError):
    """Raised when a knowledge item violates its invariants."""


class InvalidChunkError(MemoryDomainError):
    """Raised when a chunk violates its invariants."""


class InvalidDocumentReferenceError(MemoryDomainError):
    """Raised when a document reference on a knowledge item is invalid."""


class InvalidChunkGeneratorError(MemoryDomainError):
    """Raised when chunk generator configuration violates domain constraints."""
