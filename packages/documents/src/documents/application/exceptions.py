class DocumentsApplicationError(Exception):
    """Base exception for document use-case failures."""


class DocumentNotFoundError(DocumentsApplicationError):
    """Raised when a requested document does not exist."""


class ProcessingJobNotFoundError(DocumentsApplicationError):
    """Raised when a requested processing job does not exist."""


class InvalidProcessingStateError(DocumentsApplicationError):
    """Raised when a processing command cannot run in the current job state."""


class UnsupportedMimeTypeError(DocumentsApplicationError):
    """Raised when an uploaded file has a MIME type that ingestion does not support."""


class EmptyUploadError(DocumentsApplicationError):
    """Raised when an upload contains no file content."""


class UnsupportedProcessorError(DocumentsApplicationError):
    """Raised when no processor is registered for a document MIME type."""


class DocumentVersionNotFoundError(DocumentsApplicationError):
    """Raised when a requested document version does not exist."""


class DocumentProcessingError(DocumentsApplicationError):
    """Raised when document content cannot be extracted or normalized."""


class TransientDocumentProcessingError(DocumentsApplicationError):
    """Raised when processing fails due to a temporary infrastructure fault."""
