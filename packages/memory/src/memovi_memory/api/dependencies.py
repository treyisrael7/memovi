from typing import Annotated

from fastapi import Depends
from memovi_shared.fastapi import get_default_active_workspace_id
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

get_active_workspace_id = get_default_active_workspace_id


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
