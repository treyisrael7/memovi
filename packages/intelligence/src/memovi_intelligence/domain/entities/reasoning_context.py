from dataclasses import dataclass

from memovi_intelligence.domain.entities.reasoning_request import ReasoningRequest
from memovi_intelligence.domain.exceptions import InvalidReasoningContextError
from memovi_intelligence.domain.value_objects import (
    AssembledDocument,
    ContextMetadata,
    RetrievedKnowledge,
)


@dataclass(frozen=True, slots=True)
class ReasoningContext:
    """Immutable knowledge context prepared for a future reasoning provider."""

    request: ReasoningRequest
    retrieved_knowledge: tuple[RetrievedKnowledge, ...]
    assembled_documents: tuple[AssembledDocument, ...]
    metadata: ContextMetadata
    estimated_token_count: int

    def __post_init__(self) -> None:
        if any(not isinstance(item, RetrievedKnowledge) for item in self.retrieved_knowledge):
            raise InvalidReasoningContextError(
                "retrieved_knowledge must contain RetrievedKnowledge instances.",
            )
        if any(
            not isinstance(document, AssembledDocument) for document in self.assembled_documents
        ):
            raise InvalidReasoningContextError(
                "assembled_documents must contain AssembledDocument instances.",
            )
        if self.estimated_token_count < 0:
            raise InvalidReasoningContextError("estimated_token_count cannot be negative.")

        object.__setattr__(self, "retrieved_knowledge", tuple(self.retrieved_knowledge))
        object.__setattr__(self, "assembled_documents", tuple(self.assembled_documents))

    @classmethod
    def empty(cls, request: ReasoningRequest) -> ReasoningContext:
        return cls(
            request=request,
            retrieved_knowledge=(),
            assembled_documents=(),
            metadata=ContextMetadata(
                retrieved_count=0,
                retained_chunk_count=0,
                retained_document_count=0,
                truncated=False,
            ),
            estimated_token_count=0,
        )

    @property
    def query(self) -> str:
        return self.request.query.value

    @property
    def is_empty(self) -> bool:
        return len(self.retrieved_knowledge) == 0
