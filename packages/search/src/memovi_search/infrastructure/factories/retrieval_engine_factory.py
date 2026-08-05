from sqlalchemy.orm import Session as OrmSession

from memovi_search.application.services import RetrievalEngine
from memovi_search.domain.providers import EmbeddingProvider
from memovi_search.domain.ranking import RankFusion, ScoreNormalizer
from memovi_search.domain.retrievers import KeywordRetriever, SemanticRetriever
from memovi_search.infrastructure.providers import FakeEmbeddingProvider
from memovi_search.infrastructure.repositories import (
    SqlAlchemyEmbeddingRepository,
    SqlAlchemySearchRepository,
)


def build_retrieval_engine(
    session: OrmSession,
    *,
    embedding_provider: EmbeddingProvider | None = None,
) -> RetrievalEngine:
    provider = embedding_provider or FakeEmbeddingProvider()
    return RetrievalEngine(
        keyword_retriever=KeywordRetriever(
            search_repository=SqlAlchemySearchRepository(session),
        ),
        semantic_retriever=SemanticRetriever(
            embedding_provider=provider,
            embedding_repository=SqlAlchemyEmbeddingRepository(session),
        ),
        rank_fusion=RankFusion(),
        score_normalizer=ScoreNormalizer(),
    )
