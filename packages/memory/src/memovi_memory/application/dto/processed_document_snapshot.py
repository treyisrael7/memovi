from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ProcessedDocumentSnapshot:
    """Read model for processed document content consumed by memory use cases."""

    document_id: str
    document_version_id: str
    normalized_content: str | None
