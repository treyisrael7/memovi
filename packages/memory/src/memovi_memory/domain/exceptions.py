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


class InvalidKnowledgeMaterializationError(MemoryDomainError):
    """Raised when knowledge materialization input violates domain constraints."""


class InvalidCollectionIdError(MemoryDomainError):
    """Raised when a collection identifier is malformed."""


class InvalidCollectionError(MemoryDomainError):
    """Raised when a collection violates its invariants."""


class InvalidCollectionMembershipError(MemoryDomainError):
    """Raised when a collection membership violates its invariants."""


class CollectionNotFoundError(MemoryDomainError):
    """Raised when a collection cannot be found in the active workspace."""


class CollectionMembershipNotFoundError(MemoryDomainError):
    """Raised when a collection membership cannot be found."""


class DuplicateCollectionMembershipError(MemoryDomainError):
    """Raised when adding a membership that already exists."""
