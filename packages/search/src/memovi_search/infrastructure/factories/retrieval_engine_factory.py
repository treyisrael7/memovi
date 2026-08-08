from sqlalchemy.orm import Session as OrmSession

from memovi_search.application.services import RetrievalEngine
from memovi_search.domain.providers import EmbeddingProvider
from memovi_search.domain.ranking import RankFusion, ScoreNormalizer
from memovi_search.domain.retrievers import KeywordRetriever, SemanticRetriever
from memovi_search.infrastructure.repositories import (
    SqlAlchemyEmbeddingRepository,
    SqlAlchemySearchRepository,
)


def build_retrieval_engine(
    session: OrmSession,
    *,
    embedding_provider: EmbeddingProvider,
) -> RetrievalEngine:
    """Build retrieval engine with an explicitly supplied embedding provider."""
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
