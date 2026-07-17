from memovi_intelligence.domain.entities import ReasoningRequest
from memovi_intelligence.domain.value_objects import RetrievedKnowledge


class PlaceholderKnowledgeRetriever:
    """Placeholder Search-facing retriever adapter.

    Concrete Search coordination will replace this implementation later.
    """

    def retrieve(
        self,
        request: ReasoningRequest,
        *,
        limit: int,
    ) -> tuple[RetrievedKnowledge, ...]:
        raise NotImplementedError(
            "Knowledge retrieval via Search is not implemented yet.",
        )
