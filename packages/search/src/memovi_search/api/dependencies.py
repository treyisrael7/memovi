from typing import Annotated

from fastapi import Depends
from memovi_shared.fastapi import get_default_active_workspace_id
from sqlalchemy.orm import Session as OrmSession

from memovi_search.application.queries import RetrieveKnowledge, SemanticSearch
from memovi_search.infrastructure.factories import build_retrieval_engine


def get_database_session() -> OrmSession:
    raise RuntimeError("Search database session dependency was not configured.")


DatabaseSession = Annotated[OrmSession, Depends(get_database_session)]

get_active_workspace_id = get_default_active_workspace_id


def get_retrieve_knowledge(session: DatabaseSession) -> RetrieveKnowledge:
    return RetrieveKnowledge(retrieval_engine=build_retrieval_engine(session))


def get_semantic_search(session: DatabaseSession) -> SemanticSearch:
    """Deprecated: prefer get_retrieve_knowledge with mode=semantic."""

    return SemanticSearch(retrieval_engine=build_retrieval_engine(session))
