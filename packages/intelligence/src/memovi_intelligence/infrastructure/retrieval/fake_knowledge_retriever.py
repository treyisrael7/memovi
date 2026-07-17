from memovi_intelligence.domain.entities import ReasoningRequest
from memovi_intelligence.domain.value_objects import RetrievedKnowledge


class FakeKnowledgeRetriever:
    """Deterministic KnowledgeRetriever for local wiring and API tests.

    Returns a fixed knowledge chunk so the Reason pipeline can execute without a
    Search adapter. Replace with a Search-backed retriever at the composition root
    when retrieval integration lands.
    """

    DEFAULT_KNOWLEDGE = RetrievedKnowledge(
        chunk_id="chunk-memovi",
        document_id="doc-memovi",
        text="Memovi is a self-hosted knowledge platform.",
        score=0.95,
        document_title="Memovi",
    )

    def __init__(
        self,
        items: tuple[RetrievedKnowledge, ...] | None = None,
    ) -> None:
        self._items = items if items is not None else (self.DEFAULT_KNOWLEDGE,)

    def retrieve(
        self,
        request: ReasoningRequest,
        *,
        limit: int,
    ) -> tuple[RetrievedKnowledge, ...]:
        del request
        return self._items[:limit]
