from dataclasses import dataclass

from memovi_intelligence.domain.exceptions import InvalidCitationError


@dataclass(frozen=True, slots=True)
class Citation:
    """Immutable reference to knowledge that supported a reasoning answer."""

    document_id: str
    chunk_id: str
    document_title: str | None = None
    score: float | None = None

    def __post_init__(self) -> None:
        document_id = self.document_id.strip()
        chunk_id = self.chunk_id.strip()
        title = self.document_title.strip() if self.document_title is not None else None

        if not document_id:
            raise InvalidCitationError("Citation document ID is required.")
        if not chunk_id:
            raise InvalidCitationError("Citation chunk ID is required.")
        if title is not None and not title:
            raise InvalidCitationError("Citation document title cannot be blank.")
        if self.score is not None and self.score < 0:
            raise InvalidCitationError("Citation score cannot be negative.")

        object.__setattr__(self, "document_id", document_id)
        object.__setattr__(self, "chunk_id", chunk_id)
        object.__setattr__(self, "document_title", title)
