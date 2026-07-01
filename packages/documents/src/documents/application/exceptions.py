class DocumentsApplicationError(Exception):
    """Base exception for document use-case failures."""


class DocumentNotFoundError(DocumentsApplicationError):
    """Raised when a requested document does not exist."""


class ProcessingJobNotFoundError(DocumentsApplicationError):
    """Raised when a requested processing job does not exist."""


class InvalidProcessingStateError(DocumentsApplicationError):
    """Raised when a processing command cannot run in the current job state."""
