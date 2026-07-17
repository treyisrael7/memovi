from collections.abc import Callable
from datetime import UTC, datetime
from typing import cast

from memovi_search.application.commands import GenerateEmbedding
from memovi_search.application.handlers import SearchIndexedEmbeddingHandler
from memovi_search.application.ports import EventPublisher
from memovi_search.application.services import EmbeddingGenerationService
from memovi_search.domain.entities import Embedding, RankedSearchDocument, SearchDocument
from memovi_search.domain.events import EmbeddingGenerated, SearchIndexed
from memovi_search.domain.repositories import EmbeddingRepository, SearchRepository
from memovi_search.domain.value_objects import EmbeddingId, EmbeddingVector, SearchDocumentId
from memovi_search.infrastructure.providers import FakeEmbeddingProvider
from sqlalchemy.orm import Session as OrmSession

DOCUMENT_ID = "3b96152e-5ba9-4933-8819-2a08069a6d9f"
DOCUMENT_VERSION_ID = "7ce3e814-de68-4200-973e-b2526eee058d"
KNOWLEDGE_ITEM_ID = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
SOURCE_TYPE = "upload"
MIME_TYPE = "text/markdown"
SEARCHABLE_TEXT = "Indexed knowledge passage."
INDEXED_AT = datetime(2026, 7, 10, 15, 0, tzinfo=UTC)


class FakeSearchRepository(SearchRepository):
    def __init__(self, document: SearchDocument | None) -> None:
        self._document = document

    def save_document(self, search_document: SearchDocument) -> None:
        self._document = search_document

    def get_document(self, search_document_id: SearchDocumentId) -> SearchDocument | None:
        if self._document is None or self._document.id != search_document_id:
            return None
        return self._document

    def list_documents(self) -> list[SearchDocument]:
        return [] if self._document is None else [self._document]

    def delete_document(self, search_document_id: SearchDocumentId) -> None:
        raise NotImplementedError

    def search(
        self,
        query: str,
        limit: int,
        offset: int,
        *,
        document_id: str | None = None,
        document_version_id: str | None = None,
        source_type: str | None = None,
        mime_type: str | None = None,
        created_after: datetime | None = None,
        created_before: datetime | None = None,
    ) -> list[RankedSearchDocument]:
        return []


class FakeEmbeddingRepository(EmbeddingRepository):
    def __init__(self) -> None:
        self.saved: list[Embedding] = []

    def save(self, embedding: Embedding) -> None:
        self.saved.append(embedding)

    def get_by_search_document(
        self,
        search_document_id: SearchDocumentId,
    ) -> Embedding | None:
        for embedding in self.saved:
            if embedding.search_document_id == search_document_id:
                return embedding
        return None

    def delete(self, embedding_id: EmbeddingId) -> None:
        self.saved = [embedding for embedding in self.saved if embedding.id != embedding_id]

    def similarity_search(
        self,
        query_vector: EmbeddingVector,
        limit: int,
    ) -> list[RankedSearchDocument]:
        return []


class FakeEventPublisher:
    def __init__(self) -> None:
        self.published_events: list[object] = []

    def publish(self, event: object) -> None:
        self.published_events.append(event)


class FakeSession:
    def __init__(self) -> None:
        self.committed = False
        self.rolled_back = False
        self.closed = False

    def commit(self) -> None:
        self.committed = True

    def rollback(self) -> None:
        self.rolled_back = True

    def close(self) -> None:
        self.closed = True


class FakeSessionFactory:
    def __init__(self) -> None:
        self.sessions: list[FakeSession] = []

    def __call__(self) -> FakeSession:
        session = FakeSession()
        self.sessions.append(session)
        return session


def _search_document() -> SearchDocument:
    return SearchDocument(
        id=SearchDocumentId.new(),
        knowledge_item_id=KNOWLEDGE_ITEM_ID,
        document_id=DOCUMENT_ID,
        document_version_id=DOCUMENT_VERSION_ID,
        source_type=SOURCE_TYPE,
        mime_type=MIME_TYPE,
        searchable_text=SEARCHABLE_TEXT,
        created_at=INDEXED_AT,
        updated_at=INDEXED_AT,
    )


def _build_handler(
    *,
    document: SearchDocument | None,
) -> tuple[
    SearchIndexedEmbeddingHandler,
    FakeEmbeddingRepository,
    FakeEventPublisher,
    FakeSessionFactory,
]:
    search_repository = FakeSearchRepository(document)
    embedding_repository = FakeEmbeddingRepository()
    event_publisher = FakeEventPublisher()
    session_factory = FakeSessionFactory()

    def factory(session: OrmSession, publisher: EventPublisher) -> GenerateEmbedding:
        del session
        return GenerateEmbedding(
            search_repository=search_repository,
            embedding_repository=embedding_repository,
            embedding_generation_service=EmbeddingGenerationService(
                provider=FakeEmbeddingProvider(),
            ),
            event_publisher=publisher,
        )

    handler = SearchIndexedEmbeddingHandler(
        generate_embedding_factory=factory,
        event_publisher=event_publisher,
        session_factory=cast(Callable[[], OrmSession], session_factory),
    )
    return handler, embedding_repository, event_publisher, session_factory


def test_handler_generates_persists_and_publishes_embedding_generated() -> None:
    search_document = _search_document()
    handler, embedding_repository, event_publisher, session_factory = _build_handler(
        document=search_document,
    )

    handler.handle(
        SearchIndexed(
            search_document_id=search_document.id.value,
            knowledge_item_id=KNOWLEDGE_ITEM_ID,
            document_id=DOCUMENT_ID,
            document_version_id=DOCUMENT_VERSION_ID,
            indexed_at=INDEXED_AT,
        ),
    )

    assert len(embedding_repository.saved) == 1
    assert len(session_factory.sessions) == 1
    assert session_factory.sessions[0].committed is True
    assert session_factory.sessions[0].closed is True
    assert len(event_publisher.published_events) == 1
    published = event_publisher.published_events[0]
    assert isinstance(published, EmbeddingGenerated)
    assert published.search_document_id == search_document.id.value
    assert published.embedding_id == embedding_repository.saved[0].id.value
    assert published.provider == "fake"
    assert published.model == "fake-embedding-v1"
    assert published.dimensions == embedding_repository.saved[0].dimensions


def test_handler_skips_when_search_document_missing() -> None:
    handler, embedding_repository, event_publisher, session_factory = _build_handler(
        document=None,
    )

    handler.handle(
        SearchIndexed(
            search_document_id=str(SearchDocumentId.new()),
            knowledge_item_id=KNOWLEDGE_ITEM_ID,
            document_id=DOCUMENT_ID,
            document_version_id=DOCUMENT_VERSION_ID,
            indexed_at=INDEXED_AT,
        ),
    )

    assert embedding_repository.saved == []
    assert event_publisher.published_events == []
    assert session_factory.sessions[0].rolled_back is True
    assert session_factory.sessions[0].committed is False
