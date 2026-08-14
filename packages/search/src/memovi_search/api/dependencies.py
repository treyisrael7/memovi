from typing import Annotated, cast

from fastapi import Depends, Request
from memovi_shared.fastapi import get_default_active_workspace_id
from sqlalchemy.orm import Session as OrmSession

from memovi_search.application.queries import RetrieveKnowledge
from memovi_search.domain.providers import EmbeddingProvider
from memovi_search.infrastructure.factories import build_retrieval_engine


def get_database_session() -> OrmSession:
    raise RuntimeError("Search database session dependency was not configured.")


DatabaseSession = Annotated[OrmSession, Depends(get_database_session)]

get_active_workspace_id = get_default_active_workspace_id


def get_embedding_provider(request: Request) -> EmbeddingProvider:
    provider = getattr(request.app.state, "embedding_provider", None)
    if provider is None:
        raise RuntimeError("Embedding provider was not configured at application startup.")
    return cast(EmbeddingProvider, provider)


def get_retrieve_knowledge(
    session: DatabaseSession,
    embedding_provider: Annotated[EmbeddingProvider, Depends(get_embedding_provider)],
) -> RetrieveKnowledge:
    return RetrieveKnowledge(
        retrieval_engine=build_retrieval_engine(
            session,
            embedding_provider=embedding_provider,
        ),
    )
