from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session as OrmSession

from memovi_search.application.queries import RetrieveKnowledge, SemanticSearch
from memovi_search.application.services import RetrievalEngine
from memovi_search.domain.ranking import RankFusion, ScoreNormalizer
from memovi_search.domain.retrievers import KeywordRetriever, SemanticRetriever
from memovi_search.infrastructure.providers import FakeEmbeddingProvider
from memovi_search.infrastructure.repositories import (
    SqlAlchemyEmbeddingRepository,
    SqlAlchemySearchRepository,
)


def get_database_session() -> OrmSession:
    raise RuntimeError("Search database session dependency was not configured.")


DatabaseSession = Annotated[OrmSession, Depends(get_database_session)]


def build_retrieval_engine(session: OrmSession) -> RetrievalEngine:
    embedding_provider = FakeEmbeddingProvider()
    return RetrievalEngine(
        keyword_retriever=KeywordRetriever(
            search_repository=SqlAlchemySearchRepository(session),
        ),
        semantic_retriever=SemanticRetriever(
            embedding_provider=embedding_provider,
            embedding_repository=SqlAlchemyEmbeddingRepository(session),
        ),
        rank_fusion=RankFusion(),
        score_normalizer=ScoreNormalizer(),
    )


def get_retrieve_knowledge(session: DatabaseSession) -> RetrieveKnowledge:
    return RetrieveKnowledge(retrieval_engine=build_retrieval_engine(session))


def get_semantic_search(session: DatabaseSession) -> SemanticSearch:
    """Deprecated: prefer get_retrieve_knowledge with mode=semantic."""

    return SemanticSearch(retrieval_engine=build_retrieval_engine(session))
