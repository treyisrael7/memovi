from dataclasses import dataclass

from memovi_intelligence.domain.exceptions import InvalidRetrievedKnowledgeError

MAX_KNOWLEDGE_TEXT_LENGTH = 50_000


@dataclass(frozen=True, slots=True)
class RetrievedKnowledge:
    """A ranked knowledge chunk returned by retrieval for context assembly."""

    chunk_id: str
    document_id: str
    text: str
    score: float
    document_title: str | None = None

    def __post_init__(self) -> None:
        chunk_id = self.chunk_id.strip()
        document_id = self.document_id.strip()
        text = self.text.strip()
        title = self.document_title.strip() if self.document_title is not None else None

        if not chunk_id:
            raise InvalidRetrievedKnowledgeError("Retrieved knowledge chunk ID is required.")
        if not document_id:
            raise InvalidRetrievedKnowledgeError("Retrieved knowledge document ID is required.")
        if not text:
            raise InvalidRetrievedKnowledgeError("Retrieved knowledge text is required.")
        if len(text) > MAX_KNOWLEDGE_TEXT_LENGTH:
            raise InvalidRetrievedKnowledgeError(
                f"Retrieved knowledge text must be at most {MAX_KNOWLEDGE_TEXT_LENGTH} characters.",
            )
        if self.score < 0:
            raise InvalidRetrievedKnowledgeError("Retrieved knowledge score cannot be negative.")
        if title is not None and not title:
            raise InvalidRetrievedKnowledgeError(
                "Retrieved knowledge document title cannot be blank.",
            )

        object.__setattr__(self, "chunk_id", chunk_id)
        object.__setattr__(self, "document_id", document_id)
        object.__setattr__(self, "text", text)
        object.__setattr__(self, "document_title", title)
