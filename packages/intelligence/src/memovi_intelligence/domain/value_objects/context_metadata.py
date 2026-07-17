from dataclasses import dataclass

from memovi_intelligence.domain.exceptions import InvalidContextMetadataError


@dataclass(frozen=True, slots=True)
class ContextMetadata:
    """Immutable assembly statistics for a reasoning context."""

    retrieved_count: int
    retained_chunk_count: int
    retained_document_count: int
    truncated: bool
    duplicate_chunks_removed: int = 0
    duplicate_documents_skipped: int = 0

    def __post_init__(self) -> None:
        for field_name in (
            "retrieved_count",
            "retained_chunk_count",
            "retained_document_count",
            "duplicate_chunks_removed",
            "duplicate_documents_skipped",
        ):
            value = getattr(self, field_name)
            if value < 0:
                raise InvalidContextMetadataError(f"{field_name} cannot be negative.")
        if self.retained_chunk_count > self.retrieved_count:
            raise InvalidContextMetadataError(
                "retained_chunk_count cannot exceed retrieved_count.",
            )
