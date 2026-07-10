class MemoryApplicationError(Exception):
    """Base exception for memory use-case failures."""


class KnowledgeItemNotFoundError(MemoryApplicationError):
    """Raised when a requested knowledge item does not exist."""


class ChunkNotFoundError(MemoryApplicationError):
    """Raised when a requested chunk does not exist."""
