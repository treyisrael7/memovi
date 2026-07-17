from dataclasses import dataclass

from memovi_intelligence.domain.exceptions import InvalidAssembledDocumentError
from memovi_intelligence.domain.value_objects.retrieved_knowledge import RetrievedKnowledge


@dataclass(frozen=True, slots=True)
class AssembledDocument:
    """Document-level context assembled from retained retrieved chunks."""

    document_id: str
    title: str | None
    chunks: tuple[RetrievedKnowledge, ...]
    text: str
    estimated_token_count: int

    def __post_init__(self) -> None:
        document_id = self.document_id.strip()
        title = self.title.strip() if self.title is not None else None

        if not document_id:
            raise InvalidAssembledDocumentError("Assembled document ID is required.")
        if not self.chunks:
            raise InvalidAssembledDocumentError(
                "Assembled document must contain at least one chunk.",
            )
        if any(chunk.document_id != document_id for chunk in self.chunks):
            raise InvalidAssembledDocumentError(
                "Assembled document chunks must share the document ID.",
            )
        if self.estimated_token_count < 0:
            raise InvalidAssembledDocumentError(
                "Assembled document estimated token count cannot be negative.",
            )
        if title is not None and not title:
            raise InvalidAssembledDocumentError("Assembled document title cannot be blank.")

        object.__setattr__(self, "document_id", document_id)
        object.__setattr__(self, "title", title)
        object.__setattr__(self, "chunks", tuple(self.chunks))
