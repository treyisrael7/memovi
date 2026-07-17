from memovi_intelligence.domain.entities import ReasoningContext, ReasoningResult
from memovi_intelligence.domain.exceptions import InvalidReasoningContextError
from memovi_intelligence.domain.value_objects import Citation


class FakeReasoningProvider:
    """Deterministic reasoning provider for tests and local wiring.

    Produces stable answers and citations from assembled context without AI or
    network calls.
    """

    PROVIDER_NAME = "fake"
    EXECUTION_TIME = 0.0

    def reason(self, context: ReasoningContext) -> ReasoningResult:
        if context.is_empty:
            raise InvalidReasoningContextError(
                "Cannot reason over an empty reasoning context.",
            )

        citations = tuple(
            Citation(
                document_id=item.document_id,
                chunk_id=item.chunk_id,
                document_title=item.document_title,
                score=item.score,
            )
            for item in context.retrieved_knowledge
        )
        passages = " | ".join(item.text for item in context.retrieved_knowledge)
        answer = f"Answer for '{context.query}': {passages}"

        return ReasoningResult.create(
            answer=answer,
            citations=citations,
            metadata={
                "query": context.query,
                "chunk_count": len(context.retrieved_knowledge),
                "document_count": len(context.assembled_documents),
                "estimated_token_count": context.estimated_token_count,
            },
            provider=self.PROVIDER_NAME,
            execution_time=self.EXECUTION_TIME,
            context=context,
        )
