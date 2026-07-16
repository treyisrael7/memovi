from collections.abc import Callable

from memovi_memory.application.dto import KnowledgeDto
from memovi_memory.application.exceptions import KnowledgeItemNotFoundError
from memovi_memory.application.queries import GetKnowledge
from memovi_memory.domain.events import KnowledgeMaterialized
from memovi_memory.infrastructure.repositories import (
    SqlAlchemyChunkRepository,
    SqlAlchemyKnowledgeRepository,
)
from memovi_search.application.commands.materialize_search_document import MaterializeSearchDocument
from memovi_search.application.dto import KnowledgeChunkReadDto, KnowledgeMaterializedNotification
from memovi_search.application.dto.knowledge_read_dto import KnowledgeReadDto
from memovi_search.application.handlers import SearchKnowledgeMaterializedHandler
from memovi_search.application.queries import SearchKnowledge
from memovi_search.domain.services import SearchMaterializer
from memovi_search.infrastructure.repositories import SqlAlchemySearchRepository
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


def build_search_knowledge(session: OrmSession) -> SearchKnowledge:
    return SearchKnowledge(
        search_repository=SqlAlchemySearchRepository(session),
    )


def register_search_event_handlers(
    dispatcher: InProcessEventDispatcher,
    *,
    session_factory: Callable[[], OrmSession],
) -> SearchKnowledgeMaterializedHandler:
    handler = SearchKnowledgeMaterializedHandler(
        knowledge_reader=SqlAlchemyKnowledgeReader(session_factory),
        materialize_search_document_factory=build_materialize_search_document,
        event_publisher=dispatcher,
        session_factory=session_factory,
    )

    def on_knowledge_materialized(event: object) -> None:
        if not isinstance(event, KnowledgeMaterialized):
            return

        handler.handle(
            KnowledgeMaterializedNotification(
                knowledge_item_id=event.knowledge_item_id,
                document_id=event.document_id,
                document_version_id=event.document_version_id,
                occurred_at=event.occurred_at,
            ),
        )

    dispatcher.subscribe(KnowledgeMaterialized, on_knowledge_materialized)
    return handler


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
