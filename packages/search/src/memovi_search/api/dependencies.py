from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session as OrmSession

from memovi_search.application.queries import SearchKnowledge
from memovi_search.infrastructure.repositories import SqlAlchemySearchRepository


def get_database_session() -> OrmSession:
    raise RuntimeError("Search database session dependency was not configured.")


DatabaseSession = Annotated[OrmSession, Depends(get_database_session)]


def get_search_knowledge(session: DatabaseSession) -> SearchKnowledge:
    return SearchKnowledge(
        search_repository=SqlAlchemySearchRepository(session),
    )
