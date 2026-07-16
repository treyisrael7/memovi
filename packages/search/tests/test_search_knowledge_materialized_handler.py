from collections.abc import Callable
from datetime import UTC, datetime
from typing import cast

from memovi_search.application.commands import (
    MaterializeSearchDocument,
    MaterializeSearchDocumentCommand,
    MaterializeSearchDocumentResult,
)
from memovi_search.application.dto import (
    KnowledgeChunkReadDto,
    KnowledgeMaterializedNotification,
    KnowledgeReadDto,
)
from memovi_search.application.handlers import SearchKnowledgeMaterializedHandler
from memovi_search.domain.entities import Embedding, RankedSearchDocument, SearchDocument
from memovi_search.domain.events import SearchIndexed
from memovi_search.domain.repositories import SearchRepository
from memovi_search.domain.services import SearchMaterializer
from memovi_search.domain.value_objects import EmbeddingId, SearchDocumentId
from sqlalchemy.orm import Session as OrmSession

DOCUMENT_ID = "3b96152e-5ba9-4933-8819-2a08069a6d9f"
DOCUMENT_VERSION_ID = "7ce3e814-de68-4200-973e-b2526eee058d"
KNOWLEDGE_ITEM_ID = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
NOTIFICATION_AT = datetime(2026, 7, 10, 15, 0, tzinfo=UTC)


class FakeKnowledgeReader:
    def __init__(self, knowledge: KnowledgeReadDto | None) -> None:
        self._knowledge = knowledge
        self.get_knowledge_calls: list[str] = []

    def get_knowledge(self, knowledge_item_id: str) -> KnowledgeReadDto | None:
        self.get_knowledge_calls.append(knowledge_item_id)
        return self._knowledge


class FakeSearchRepository(SearchRepository):
    def __init__(self, operations: list[str]) -> None:
        self._operations = operations
        self.saved_documents: list[SearchDocument] = []

    def save_document(self, search_document: SearchDocument) -> None:
        self._operations.append("document_save")
        self.saved_documents.append(search_document)

    def get_document(self, search_document_id: SearchDocumentId) -> SearchDocument | None:
        return None

    def list_documents(self) -> list[SearchDocument]:
        return self.saved_documents

    def delete_document(self, search_document_id: SearchDocumentId) -> None:
        raise NotImplementedError

    def search(self, query: str, limit: int, offset: int) -> list[RankedSearchDocument]:
        return []

    def save_embedding(self, embedding: Embedding) -> None:
        raise NotImplementedError

    def get_embedding(self, embedding_id: EmbeddingId) -> Embedding | None:
        return None

    def delete_embedding(self, embedding_id: EmbeddingId) -> None:
        raise NotImplementedError


class FakeEventPublisher:
    def __init__(self) -> None:
        self.published_events: list[object] = []

    def publish(self, event: object) -> None:
        self.published_events.append(event)


class FakeSession:
    def commit(self) -> None:
        return None

    def rollback(self) -> None:
        return None

    def close(self) -> None:
        return None


class FakeSessionFactory:
    def __init__(self) -> None:
        self.sessions: list[FakeSession] = []

    def __call__(self) -> FakeSession:
        session = FakeSession()
        self.sessions.append(session)
        return session


class SpyMaterializeSearchDocument:
    def __init__(self, inner: MaterializeSearchDocument) -> None:
        self._inner = inner
        self.execute_calls: list[MaterializeSearchDocumentCommand] = []

    def execute(self, command: MaterializeSearchDocumentCommand) -> MaterializeSearchDocumentResult:
        self.execute_calls.append(command)
        return self._inner.execute(command)


def _knowledge_read_dto(*, chunks: tuple[KnowledgeChunkReadDto, ...]) -> KnowledgeReadDto:
    return KnowledgeReadDto(
        id=KNOWLEDGE_ITEM_ID,
        document_id=DOCUMENT_ID,
        document_version_id=DOCUMENT_VERSION_ID,
        chunks=chunks,
    )


def _build_handler(
    *,
    knowledge: KnowledgeReadDto | None,
    operations: list[str],
) -> tuple[
    SearchKnowledgeMaterializedHandler,
    FakeKnowledgeReader,
    SpyMaterializeSearchDocument,
    FakeSearchRepository,
    FakeEventPublisher,
]:
    knowledge_reader = FakeKnowledgeReader(knowledge)
    operations_list = operations
    search_repository = FakeSearchRepository(operations_list)
    event_publisher = FakeEventPublisher()
    materialize = SpyMaterializeSearchDocument(
        MaterializeSearchDocument(
            search_materializer=SearchMaterializer(),
            search_repository=search_repository,
        ),
    )
    session_factory = FakeSessionFactory()

    handler = SearchKnowledgeMaterializedHandler(
        knowledge_reader=knowledge_reader,
        materialize_search_document_factory=lambda _session: cast(
            MaterializeSearchDocument,
            materialize,
        ),
        event_publisher=event_publisher,
        session_factory=cast(Callable[[], OrmSession], session_factory),
    )
    return handler, knowledge_reader, materialize, search_repository, event_publisher


def test_handler_materializes_persists_and_publishes_search_indexed() -> None:
    operations: list[str] = []
    handler, knowledge_reader, materialize, search_repository, event_publisher = _build_handler(
        knowledge=_knowledge_read_dto(
            chunks=(
                KnowledgeChunkReadDto(chunk_index=0, text="Alpha."),
                KnowledgeChunkReadDto(chunk_index=1, text="Beta."),
            ),
        ),
        operations=operations,
    )

    handler.handle(
        KnowledgeMaterializedNotification(
            knowledge_item_id=KNOWLEDGE_ITEM_ID,
            document_id=DOCUMENT_ID,
            document_version_id=DOCUMENT_VERSION_ID,
            occurred_at=NOTIFICATION_AT,
        )
    )

    assert knowledge_reader.get_knowledge_calls == [KNOWLEDGE_ITEM_ID]
    assert len(materialize.execute_calls) == 1
    assert materialize.execute_calls[0].chunk_texts == ["Alpha.", "Beta."]
    assert operations == ["document_save"]
    assert len(search_repository.saved_documents) == 1
    assert len(event_publisher.published_events) == 1
    indexed = event_publisher.published_events[0]
    assert isinstance(indexed, SearchIndexed)
    assert indexed.knowledge_item_id == KNOWLEDGE_ITEM_ID
    assert indexed.search_document_id == search_repository.saved_documents[0].id.value


def test_handler_skips_persistence_when_knowledge_is_missing() -> None:
    operations: list[str] = []
    handler, knowledge_reader, materialize, _, event_publisher = _build_handler(
        knowledge=None,
        operations=operations,
    )

    handler.handle(
        KnowledgeMaterializedNotification(
            knowledge_item_id=KNOWLEDGE_ITEM_ID,
            document_id=DOCUMENT_ID,
            document_version_id=DOCUMENT_VERSION_ID,
            occurred_at=NOTIFICATION_AT,
        )
    )

    assert knowledge_reader.get_knowledge_calls == [KNOWLEDGE_ITEM_ID]
    assert materialize.execute_calls == []
    assert operations == []
    assert event_publisher.published_events == []


def test_handler_skips_search_indexed_when_searchable_text_is_empty() -> None:
    operations: list[str] = []
    handler, _, materialize, search_repository, event_publisher = _build_handler(
        knowledge=_knowledge_read_dto(
            chunks=(KnowledgeChunkReadDto(chunk_index=0, text="   "),),
        ),
        operations=operations,
    )

    handler.handle(
        KnowledgeMaterializedNotification(
            knowledge_item_id=KNOWLEDGE_ITEM_ID,
            document_id=DOCUMENT_ID,
            document_version_id=DOCUMENT_VERSION_ID,
            occurred_at=NOTIFICATION_AT,
        )
    )

    assert len(materialize.execute_calls) == 1
    assert operations == []
    assert search_repository.saved_documents == []
    assert event_publisher.published_events == []
