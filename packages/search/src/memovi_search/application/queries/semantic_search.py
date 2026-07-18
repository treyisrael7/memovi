"""Deprecated semantic-only query; prefer RetrieveKnowledge with mode=semantic."""

from dataclasses import dataclass

from memovi_shared import WorkspaceId

from memovi_search.application.dto import SearchResultDto
from memovi_search.application.queries.retrieve_knowledge import (
    RetrieveKnowledge,
    RetrieveKnowledgeQuery,
)
from memovi_search.application.services.retrieval_engine import RetrievalEngine, RetrievalMode


@dataclass(frozen=True, slots=True)
class SemanticSearchQuery:
    query: str
    workspace_id: WorkspaceId
    limit: int


class SemanticSearch:
    """Thin semantic-mode adapter over RetrieveKnowledge for transitional callers."""

    def __init__(self, *, retrieval_engine: RetrievalEngine) -> None:
        self._retrieve_knowledge = RetrieveKnowledge(retrieval_engine=retrieval_engine)

    def execute(self, query: SemanticSearchQuery) -> list[SearchResultDto]:
        return self._retrieve_knowledge.execute(
            RetrieveKnowledgeQuery(
                query=query.query,
                workspace_id=query.workspace_id,
                limit=query.limit,
                offset=0,
                mode=RetrievalMode.SEMANTIC,
            )
        )
