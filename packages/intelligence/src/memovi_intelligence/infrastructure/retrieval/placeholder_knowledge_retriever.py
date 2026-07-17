from memovi_intelligence.domain.entities import ReasoningContext, ReasoningRequest


class PlaceholderKnowledgeRetriever:
    """Placeholder Search-facing retriever adapter.

    Concrete Search coordination will replace this implementation later.
    """

    def retrieve(self, request: ReasoningRequest, *, limit: int) -> ReasoningContext:
        raise NotImplementedError(
            "Knowledge retrieval via Search is not implemented yet.",
        )
