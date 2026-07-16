from collections.abc import Callable
from datetime import UTC, datetime

from sqlalchemy.orm import Session as OrmSession

from memovi_search.application.commands.materialize_search_document import (
    MaterializeSearchDocument,
    MaterializeSearchDocumentCommand,
)
from memovi_search.application.dto.knowledge_materialized_notification import (
    KnowledgeMaterializedNotification,
)
from memovi_search.application.ports import EventPublisher, KnowledgeReader
from memovi_search.domain.events import SearchIndexed
from memovi_search.domain.exceptions import InvalidSearchMaterializationError


class SearchKnowledgeMaterializedHandler:
    """Materializes search documents when canonical knowledge is materialized."""

    def __init__(
        self,
        *,
        knowledge_reader: KnowledgeReader,
        materialize_search_document_factory: Callable[[OrmSession], MaterializeSearchDocument],
        event_publisher: EventPublisher,
        session_factory: Callable[[], OrmSession],
    ) -> None:
        self._knowledge_reader = knowledge_reader
        self._materialize_search_document_factory = materialize_search_document_factory
        self._event_publisher = event_publisher
        self._session_factory = session_factory

    def handle(self, notification: KnowledgeMaterializedNotification) -> None:
        knowledge = self._knowledge_reader.get_knowledge(notification.knowledge_item_id)
        if knowledge is None:
            return

        chunk_texts = [
            chunk.text for chunk in sorted(knowledge.chunks, key=lambda chunk: chunk.chunk_index)
        ]

        session = self._session_factory()
        try:
            result = self._materialize_search_document_factory(session).execute(
                MaterializeSearchDocumentCommand(
                    knowledge_item_id=knowledge.id,
                    document_id=knowledge.document_id,
                    document_version_id=knowledge.document_version_id,
                    source_type=knowledge.source_type,
                    mime_type=knowledge.mime_type,
                    chunk_texts=chunk_texts,
                ),
            )
            session.commit()
        except InvalidSearchMaterializationError:
            session.rollback()
            return
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

        self._event_publisher.publish(
            SearchIndexed(
                search_document_id=result.search_document_id,
                knowledge_item_id=knowledge.id,
                document_id=knowledge.document_id,
                document_version_id=knowledge.document_version_id,
                indexed_at=datetime.now(UTC),
            ),
        )
