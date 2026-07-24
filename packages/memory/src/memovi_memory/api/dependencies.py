from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from memovi_shared import DEFAULT_WORKSPACE_ID, InvalidWorkspaceIdError, WorkspaceId
from sqlalchemy.orm import Session as OrmSession

from memovi_memory.application.queries import (
    GetKnowledge,
    GetKnowledgeDashboard,
    ListConcepts,
    ListDocumentKnowledge,
    ListKnowledge,
    ListRelationships,
)
from memovi_memory.infrastructure.repositories import (
    SqlAlchemyChunkRepository,
    SqlAlchemyKnowledgeRepository,
)


def get_database_session() -> OrmSession:
    raise RuntimeError("Memory database session dependency was not configured.")


DatabaseSession = Annotated[OrmSession, Depends(get_database_session)]

WORKSPACE_HEADER = "X-Memovi-Workspace-Id"


def get_active_workspace_id(
    x_memovi_workspace_id: Annotated[str | None, Header(alias=WORKSPACE_HEADER)] = None,
) -> WorkspaceId:
    """Package default workspace resolution; composition root may override."""
    if x_memovi_workspace_id is None or not x_memovi_workspace_id.strip():
        return DEFAULT_WORKSPACE_ID
    try:
        return WorkspaceId(x_memovi_workspace_id.strip())
    except InvalidWorkspaceIdError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc


def get_list_knowledge(session: DatabaseSession) -> ListKnowledge:
    return ListKnowledge(
        knowledge_repository=SqlAlchemyKnowledgeRepository(session),
        chunk_repository=SqlAlchemyChunkRepository(session),
    )


def get_get_knowledge(session: DatabaseSession) -> GetKnowledge:
    return GetKnowledge(
        knowledge_repository=SqlAlchemyKnowledgeRepository(session),
        chunk_repository=SqlAlchemyChunkRepository(session),
    )


def get_list_document_knowledge(session: DatabaseSession) -> ListDocumentKnowledge:
    return ListDocumentKnowledge(
        knowledge_repository=SqlAlchemyKnowledgeRepository(session),
        chunk_repository=SqlAlchemyChunkRepository(session),
    )


def get_list_concepts(
    list_knowledge: Annotated[ListKnowledge, Depends(get_list_knowledge)],
) -> ListConcepts:
    return ListConcepts(list_knowledge=list_knowledge)


def get_list_relationships(
    list_knowledge: Annotated[ListKnowledge, Depends(get_list_knowledge)],
) -> ListRelationships:
    return ListRelationships(list_knowledge=list_knowledge)


def get_knowledge_dashboard(
    list_knowledge: Annotated[ListKnowledge, Depends(get_list_knowledge)],
    list_concepts: Annotated[ListConcepts, Depends(get_list_concepts)],
    list_relationships: Annotated[ListRelationships, Depends(get_list_relationships)],
) -> GetKnowledgeDashboard:
    return GetKnowledgeDashboard(
        list_knowledge=list_knowledge,
        list_concepts=list_concepts,
        list_relationships=list_relationships,
    )
