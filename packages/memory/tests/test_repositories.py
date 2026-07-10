from datetime import UTC, datetime

from memovi_memory.domain.entities import Chunk, KnowledgeItem
from memovi_memory.domain.value_objects import ChunkIndex, KnowledgeItemId
from memovi_memory.infrastructure.persistence.models import Base
from memovi_memory.infrastructure.repositories import (
    SqlAlchemyChunkRepository,
    SqlAlchemyKnowledgeRepository,
)
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

DOCUMENT_ID = "d62fa912-48a9-4d57-abf2-40a137f48ffa"
DOCUMENT_VERSION_ID = "7d086319-ee8e-4fe5-9fc3-30eddad79749"


def _build_session_factory() -> tuple[sessionmaker[Session], Engine]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False), engine


def test_knowledge_repository_round_trips_save_get_list_and_delete() -> None:
    session_factory, engine = _build_session_factory()
    timestamp = datetime(2026, 7, 9, 23, 0, tzinfo=UTC)
    knowledge_item = KnowledgeItem(
        id=KnowledgeItemId.new(),
        document_id=DOCUMENT_ID,
        document_version_id=DOCUMENT_VERSION_ID,
        created_at=timestamp,
        updated_at=timestamp,
    )

    with session_factory() as session:
        repository = SqlAlchemyKnowledgeRepository(session)
        repository.save(knowledge_item)
        session.commit()

    with session_factory() as session:
        repository = SqlAlchemyKnowledgeRepository(session)
        loaded = repository.get_by_id(knowledge_item.id)
        listed = repository.list_by_document_version(
            document_id=DOCUMENT_ID,
            document_version_id=DOCUMENT_VERSION_ID,
        )

        assert loaded is not None
        assert loaded.document_id == DOCUMENT_ID
        assert loaded.created_at.tzinfo is UTC
        assert len(listed) == 1
        assert listed[0].id == knowledge_item.id

    updated = knowledge_item.touch(datetime(2026, 7, 9, 23, 30, tzinfo=UTC))
    with session_factory() as session:
        repository = SqlAlchemyKnowledgeRepository(session)
        repository.save(updated)
        session.commit()

    with session_factory() as session:
        repository = SqlAlchemyKnowledgeRepository(session)
        loaded = repository.get_by_id(knowledge_item.id)
        assert loaded is not None
        assert loaded.updated_at == datetime(2026, 7, 9, 23, 30, tzinfo=UTC)

        repository.delete(knowledge_item.id)
        session.commit()

    with session_factory() as session:
        repository = SqlAlchemyKnowledgeRepository(session)
        assert repository.get_by_id(knowledge_item.id) is None
        assert (
            repository.list_by_document_version(
                document_id=DOCUMENT_ID,
                document_version_id=DOCUMENT_VERSION_ID,
            )
            == []
        )

    engine.dispose()


def test_chunk_repository_round_trips_save_many_list_and_delete() -> None:
    session_factory, engine = _build_session_factory()
    knowledge_item_id = KnowledgeItemId.new()
    first = Chunk.create(
        document_id=DOCUMENT_ID,
        document_version_id=DOCUMENT_VERSION_ID,
        chunk_index=ChunkIndex(0),
        text=" First chunk. ",
        knowledge_item_id=knowledge_item_id,
    )
    second = Chunk.create(
        document_id=DOCUMENT_ID,
        document_version_id=DOCUMENT_VERSION_ID,
        chunk_index=ChunkIndex(1),
        text="Second chunk.",
        knowledge_item_id=knowledge_item_id,
    )

    with session_factory() as session:
        repository = SqlAlchemyChunkRepository(session)
        repository.save_many([first, second])
        session.commit()

    with session_factory() as session:
        repository = SqlAlchemyChunkRepository(session)
        loaded = repository.list_by_document_version(
            document_id=DOCUMENT_ID,
            document_version_id=DOCUMENT_VERSION_ID,
        )

        assert len(loaded) == 2
        assert loaded[0].text == "First chunk."
        assert loaded[0].knowledge_item_id == knowledge_item_id
        assert loaded[1].chunk_index.value == 1

    updated_second = Chunk(
        id=second.id,
        knowledge_item_id=knowledge_item_id,
        document_id=DOCUMENT_ID,
        document_version_id=DOCUMENT_VERSION_ID,
        chunk_index=ChunkIndex(1),
        text="Updated second chunk.",
        created_at=second.created_at,
    )
    with session_factory() as session:
        repository = SqlAlchemyChunkRepository(session)
        repository.save_many([updated_second])
        session.commit()

    with session_factory() as session:
        repository = SqlAlchemyChunkRepository(session)
        loaded = repository.list_by_document_version(
            document_id=DOCUMENT_ID,
            document_version_id=DOCUMENT_VERSION_ID,
        )
        assert loaded[1].text == "Updated second chunk."

        repository.delete_by_document_version(
            document_id=DOCUMENT_ID,
            document_version_id=DOCUMENT_VERSION_ID,
        )
        session.commit()

    with session_factory() as session:
        repository = SqlAlchemyChunkRepository(session)
        assert (
            repository.list_by_document_version(
                document_id=DOCUMENT_ID,
                document_version_id=DOCUMENT_VERSION_ID,
            )
            == []
        )

    engine.dispose()
