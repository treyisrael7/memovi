from collections.abc import Callable

from sqlalchemy.orm import Session as OrmSession

from memovi_search.application.commands.generate_embedding import (
    GenerateEmbedding,
    GenerateEmbeddingCommand,
)
from memovi_search.application.exceptions import SearchDocumentNotFoundError
from memovi_search.application.ports import EventPublisher
from memovi_search.domain.events import SearchIndexed


class _DeferredEventPublisher:
    """Buffers events until the surrounding unit of work commits."""

    def __init__(self) -> None:
        self.events: list[object] = []

    def publish(self, event: object) -> None:
        self.events.append(event)


class SearchIndexedEmbeddingHandler:
    """Generates embedding projections when a search document is indexed."""

    def __init__(
        self,
        *,
        generate_embedding_factory: Callable[
            [OrmSession, EventPublisher],
            GenerateEmbedding,
        ],
        event_publisher: EventPublisher,
        session_factory: Callable[[], OrmSession],
    ) -> None:
        self._generate_embedding_factory = generate_embedding_factory
        self._event_publisher = event_publisher
        self._session_factory = session_factory

    def handle(self, event: SearchIndexed) -> None:
        deferred = _DeferredEventPublisher()
        session = self._session_factory()
        try:
            self._generate_embedding_factory(session, deferred).execute(
                GenerateEmbeddingCommand(search_document_id=event.search_document_id),
            )
            session.commit()
        except SearchDocumentNotFoundError:
            session.rollback()
            return
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

        for published_event in deferred.events:
            self._event_publisher.publish(published_event)
