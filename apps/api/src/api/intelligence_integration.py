"""Composition-root wiring for Intelligence integrations.

Owns adapters and DI factories that connect Intelligence ports to platform
infrastructure (Search retrieval, durable conversation persistence) without
introducing cross-domain package imports.
"""

from typing import Annotated

from fastapi import Depends
from memovi_intelligence.api.dependencies import (
    get_database_session as get_intelligence_database_session,
)
from memovi_intelligence.application.ports import ConversationRepository
from memovi_intelligence.domain.entities import ReasoningRequest
from memovi_intelligence.domain.value_objects import RetrievedKnowledge
from memovi_intelligence.infrastructure import SqlAlchemyConversationRepository
from memovi_search.api.dependencies import get_database_session as get_search_database_session
from memovi_search.application.dto import SearchResultDto
from memovi_search.application.queries import RetrieveKnowledge, RetrieveKnowledgeQuery
from memovi_search.application.services import RetrievalMode
from memovi_shared import WorkspaceId
from sqlalchemy.orm import Session as OrmSession

from api.search_integration import build_retrieve_knowledge
from api.workspace_context import get_active_workspace_id


def get_sqlalchemy_conversation_repository(
    session: Annotated[OrmSession, Depends(get_intelligence_database_session)],
) -> ConversationRepository:
    """Request-scoped durable ConversationRepository for the composition root."""
    return SqlAlchemyConversationRepository(session)


class SearchKnowledgeRetriever:
    """Adapts Search RetrieveKnowledge to the Intelligence KnowledgeRetriever port."""

    def __init__(
        self,
        *,
        retrieve_knowledge: RetrieveKnowledge,
        workspace_id: WorkspaceId,
        mode: RetrievalMode = RetrievalMode.HYBRID,
    ) -> None:
        self._retrieve_knowledge = retrieve_knowledge
        self._workspace_id = workspace_id
        self._mode = mode

    def retrieve(
        self,
        request: ReasoningRequest,
        *,
        limit: int,
    ) -> tuple[RetrievedKnowledge, ...]:
        results = self._retrieve_knowledge.execute(
            RetrieveKnowledgeQuery(
                query=request.query.value,
                workspace_id=self._workspace_id,
                limit=limit,
                mode=self._mode,
            ),
        )
        return tuple(_to_retrieved_knowledge(result) for result in results)


def get_search_knowledge_retriever(
    session: Annotated[OrmSession, Depends(get_search_database_session)],
    workspace_id: Annotated[WorkspaceId, Depends(get_active_workspace_id)],
) -> SearchKnowledgeRetriever:
    """Request-scoped Search-backed KnowledgeRetriever for the composition root."""
    return SearchKnowledgeRetriever(
        retrieve_knowledge=build_retrieve_knowledge(session),
        workspace_id=workspace_id,
    )


def _to_retrieved_knowledge(result: SearchResultDto) -> RetrievedKnowledge:
    """Map Search identity, text, and score into RetrievedKnowledge.

    Search has no document title; PromptBuilder falls back to document_id for
    citation display. knowledge_item_id stays on the Search DTO boundary.
    """
    return RetrievedKnowledge(
        chunk_id=result.search_document_id,
        document_id=result.document_id,
        text=result.searchable_text,
        score=result.relevance_score,
        document_title=None,
    )
