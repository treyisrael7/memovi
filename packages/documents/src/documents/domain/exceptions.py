class DocumentsDomainError(Exception):
    """Base exception for document domain invariant failures."""


class InvalidDocumentIdError(DocumentsDomainError):
    """Raised when a document identifier is malformed."""


class InvalidDocumentNameError(DocumentsDomainError):
    """Raised when a document name violates domain constraints."""


class InvalidMimeTypeError(DocumentsDomainError):
    """Raised when a MIME type is not a valid normalized value."""


class InvalidSourceTypeError(DocumentsDomainError):
    """Raised when a source type is not a recognized document origin."""


class InvalidDocumentVersionError(DocumentsDomainError):
    """Raised when a document version violates its invariants."""


class InvalidProcessingJobError(DocumentsDomainError):
    """Raised when a processing job violates its invariants."""


class InvalidProcessingTransitionError(DocumentsDomainError):
    """Raised when a processing job cannot transition to the requested status."""
