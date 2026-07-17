from collections.abc import Callable

from memovi_memory.application.dto import KnowledgeDto
from memovi_memory.application.exceptions import KnowledgeItemNotFoundError
from memovi_memory.application.queries import GetKnowledge
from memovi_memory.domain.events import KnowledgeMaterialized
from memovi_memory.infrastructure.repositories import (
    SqlAlchemyChunkRepository,
    SqlAlchemyKnowledgeRepository,
)
from memovi_search.application.commands.generate_embedding import GenerateEmbedding
from memovi_search.application.commands.materialize_search_document import MaterializeSearchDocument
from memovi_search.application.dto import KnowledgeChunkReadDto, KnowledgeMaterializedNotification
from memovi_search.application.dto.knowledge_read_dto import KnowledgeReadDto
from memovi_search.application.handlers import (
    SearchIndexedEmbeddingHandler,
    SearchKnowledgeMaterializedHandler,
)
from memovi_search.application.ports import EventPublisher
from memovi_search.application.queries import RetrieveKnowledge, SearchKnowledge, SemanticSearch
from memovi_search.application.services import EmbeddingGenerationService, RetrievalEngine
from memovi_search.domain.events import SearchIndexed
from memovi_search.domain.providers import EmbeddingProvider
from memovi_search.domain.ranking import RankFusion, ScoreNormalizer
from memovi_search.domain.retrievers import KeywordRetriever, SemanticRetriever
from memovi_search.domain.services import SearchMaterializer
from memovi_search.infrastructure.providers import FakeEmbeddingProvider
from memovi_search.infrastructure.repositories import (
    SqlAlchemyEmbeddingRepository,
    SqlAlchemySearchRepository,
)
from sqlalchemy.orm import Session as OrmSession

from api.events import InProcessEventDispatcher


class SqlAlchemyKnowledgeReader:
    """Loads canonical knowledge through the memory persistence layer."""

    def __init__(self, session_factory: Callable[[], OrmSession]) -> None:
        self._session_factory = session_factory

    def get_knowledge(self, knowledge_item_id: str) -> KnowledgeReadDto | None:
        session = self._session_factory()
        try:
            knowledge = GetKnowledge(
                knowledge_repository=SqlAlchemyKnowledgeRepository(session),
                chunk_repository=SqlAlchemyChunkRepository(session),
            ).execute(knowledge_item_id)
        except KnowledgeItemNotFoundError:
            return None
        finally:
            session.close()

        return _to_knowledge_read_dto(knowledge)


def build_materialize_search_document(session: OrmSession) -> MaterializeSearchDocument:
    return MaterializeSearchDocument(
        search_materializer=SearchMaterializer(),
        search_repository=SqlAlchemySearchRepository(session),
    )


def build_generate_embedding(
    session: OrmSession,
    event_publisher: EventPublisher,
    *,
    embedding_provider: EmbeddingProvider,
) -> GenerateEmbedding:
    return GenerateEmbedding(
        search_repository=SqlAlchemySearchRepository(session),
        embedding_repository=SqlAlchemyEmbeddingRepository(session),
        embedding_generation_service=EmbeddingGenerationService(provider=embedding_provider),
        event_publisher=event_publisher,
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


def build_retrieve_knowledge(
    session: OrmSession,
    *,
    embedding_provider: EmbeddingProvider | None = None,
) -> RetrieveKnowledge:
    return RetrieveKnowledge(
        retrieval_engine=build_retrieval_engine(
            session,
            embedding_provider=embedding_provider,
        ),
    )


def build_search_knowledge(
    session: OrmSession,
    *,
    embedding_provider: EmbeddingProvider | None = None,
) -> SearchKnowledge:
    return SearchKnowledge(
        retrieval_engine=build_retrieval_engine(
            session,
            embedding_provider=embedding_provider,
        ),
    )


def build_semantic_search(
    session: OrmSession,
    *,
    embedding_provider: EmbeddingProvider | None = None,
) -> SemanticSearch:
    return SemanticSearch(
        retrieval_engine=build_retrieval_engine(
            session,
            embedding_provider=embedding_provider,
        ),
    )


def register_search_event_handlers(
    dispatcher: InProcessEventDispatcher,
    *,
    session_factory: Callable[[], OrmSession],
    embedding_provider: EmbeddingProvider | None = None,
) -> tuple[SearchKnowledgeMaterializedHandler, SearchIndexedEmbeddingHandler]:
    provider = embedding_provider or FakeEmbeddingProvider()

    materialize_handler = SearchKnowledgeMaterializedHandler(
        knowledge_reader=SqlAlchemyKnowledgeReader(session_factory),
        materialize_search_document_factory=build_materialize_search_document,
        event_publisher=dispatcher,
        session_factory=session_factory,
    )

    embedding_handler = SearchIndexedEmbeddingHandler(
        generate_embedding_factory=lambda session, event_publisher: build_generate_embedding(
            session,
            event_publisher,
            embedding_provider=provider,
        ),
        event_publisher=dispatcher,
        session_factory=session_factory,
    )

    def on_knowledge_materialized(event: object) -> None:
        if not isinstance(event, KnowledgeMaterialized):
            return

        materialize_handler.handle(
            KnowledgeMaterializedNotification(
                knowledge_item_id=event.knowledge_item_id,
                document_id=event.document_id,
                document_version_id=event.document_version_id,
                occurred_at=event.occurred_at,
            ),
        )

    def on_search_indexed(event: object) -> None:
        if not isinstance(event, SearchIndexed):
            return
        embedding_handler.handle(event)

    dispatcher.subscribe(KnowledgeMaterialized, on_knowledge_materialized)
    dispatcher.subscribe(SearchIndexed, on_search_indexed)
    return materialize_handler, embedding_handler


def _to_knowledge_read_dto(knowledge: KnowledgeDto) -> KnowledgeReadDto:
    return KnowledgeReadDto(
        id=knowledge.id,
        document_id=knowledge.document_id,
        document_version_id=knowledge.document_version_id,
        source_type=knowledge.source_type,
        mime_type=knowledge.mime_type,
        chunks=tuple(
            KnowledgeChunkReadDto(
                chunk_index=chunk.chunk_index,
                text=chunk.text,
            )
            for chunk in knowledge.chunks
        ),
    )
