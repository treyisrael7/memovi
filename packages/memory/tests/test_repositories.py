from datetime import UTC, datetime

from memovi_memory.domain.entities import Chunk, KnowledgeItem
from memovi_memory.domain.value_objects import ChunkIndex, KnowledgeItemId
from memovi_memory.infrastructure.persistence.models import Base
from memovi_memory.infrastructure.repositories import (
    SqlAlchemyChunkRepository,
    SqlAlchemyKnowledgeRepository,
)
from memovi_shared import WorkspaceId
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

DOCUMENT_ID = "d62fa912-48a9-4d57-abf2-40a137f48ffa"
DOCUMENT_VERSION_ID = "7d086319-ee8e-4fe5-9fc3-30eddad79749"
OTHER_DOCUMENT_ID = "8e1b0f2a-1c3d-4e5f-9a0b-1c2d3e4f5a6b"
OTHER_DOCUMENT_VERSION_ID = "9f086319-ee8e-4fe5-9fc3-30eddad79750"
SOURCE_TYPE = "upload"
MIME_TYPE = "text/markdown"


def _build_session_factory() -> tuple[sessionmaker[Session], Engine]:
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    return (sessionmaker(bind=engine, expire_on_commit=False), engine)


def test_knowledge_repository_round_trips_save_get_list_and_delete() -> None:
    session_factory, engine = _build_session_factory()
    timestamp = datetime(2026, 7, 9, 23, 0, tzinfo=UTC)
    knowledge_item = KnowledgeItem(
        id=KnowledgeItemId.new(),
        document_id=DOCUMENT_ID,
        document_version_id=DOCUMENT_VERSION_ID,
        source_type=SOURCE_TYPE,
        mime_type=MIME_TYPE,
        created_at=timestamp,
        updated_at=timestamp,
        workspace_id=WorkspaceId.default(),
    )
    with session_factory() as session:
        repository = SqlAlchemyKnowledgeRepository(session)
        repository.save(knowledge_item)
        session.commit()
    with session_factory() as session:
        repository = SqlAlchemyKnowledgeRepository(session)
        loaded = repository.get_by_id(knowledge_item.id, workspace_id=WorkspaceId.default())
        listed = repository.list_by_document_version(
            workspace_id=WorkspaceId.default(),
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
        loaded = repository.get_by_id(knowledge_item.id, workspace_id=WorkspaceId.default())
        assert loaded is not None
        assert loaded.updated_at == datetime(2026, 7, 9, 23, 30, tzinfo=UTC)
        repository.delete(knowledge_item.id, workspace_id=WorkspaceId.default())
        session.commit()
    with session_factory() as session:
        repository = SqlAlchemyKnowledgeRepository(session)
        assert repository.get_by_id(knowledge_item.id, workspace_id=WorkspaceId.default()) is None
        assert (
            repository.list_by_document_version(
                workspace_id=WorkspaceId.default(),
                document_id=DOCUMENT_ID,
                document_version_id=DOCUMENT_VERSION_ID,
            )
            == []
        )
    engine.dispose()


def test_knowledge_repository_lists_all_and_by_document() -> None:
    session_factory, engine = _build_session_factory()
    earlier = datetime(2026, 7, 10, 10, 0, tzinfo=UTC)
    later = datetime(2026, 7, 10, 11, 0, tzinfo=UTC)
    first_item = KnowledgeItem(
        id=KnowledgeItemId.new(),
        document_id=DOCUMENT_ID,
        document_version_id=DOCUMENT_VERSION_ID,
        source_type=SOURCE_TYPE,
        mime_type=MIME_TYPE,
        created_at=earlier,
        updated_at=earlier,
        workspace_id=WorkspaceId.default(),
    )
    second_item = KnowledgeItem(
        id=KnowledgeItemId.new(),
        document_id=DOCUMENT_ID,
        document_version_id=OTHER_DOCUMENT_VERSION_ID,
        source_type=SOURCE_TYPE,
        mime_type=MIME_TYPE,
        created_at=later,
        updated_at=later,
        workspace_id=WorkspaceId.default(),
    )
    third_item = KnowledgeItem(
        id=KnowledgeItemId.new(),
        document_id=OTHER_DOCUMENT_ID,
        document_version_id=DOCUMENT_VERSION_ID,
        source_type=SOURCE_TYPE,
        mime_type=MIME_TYPE,
        created_at=later,
        updated_at=later,
        workspace_id=WorkspaceId.default(),
    )
    with session_factory() as session:
        repository = SqlAlchemyKnowledgeRepository(session)
        repository.save(first_item)
        repository.save(second_item)
        repository.save(third_item)
        session.commit()
    with session_factory() as session:
        repository = SqlAlchemyKnowledgeRepository(session)
        all_items = repository.list_by_workspace(workspace_id=WorkspaceId.default())
        document_items = repository.list_by_document(
            workspace_id=WorkspaceId.default(),
            document_id=DOCUMENT_ID,
        )
        assert [item.id for item in all_items] == [first_item.id, second_item.id, third_item.id]
        assert [item.id for item in document_items] == [first_item.id, second_item.id]
    engine.dispose()


def test_knowledge_repository_hides_items_from_other_workspaces() -> None:
    session_factory, engine = _build_session_factory()
    other_workspace = WorkspaceId.new()
    timestamp = datetime(2026, 7, 10, 12, 0, tzinfo=UTC)
    owned = KnowledgeItem(
        id=KnowledgeItemId.new(),
        document_id=DOCUMENT_ID,
        document_version_id=DOCUMENT_VERSION_ID,
        source_type=SOURCE_TYPE,
        mime_type=MIME_TYPE,
        created_at=timestamp,
        updated_at=timestamp,
        workspace_id=WorkspaceId.default(),
    )
    foreign = KnowledgeItem(
        id=KnowledgeItemId.new(),
        document_id=OTHER_DOCUMENT_ID,
        document_version_id=OTHER_DOCUMENT_VERSION_ID,
        source_type=SOURCE_TYPE,
        mime_type=MIME_TYPE,
        created_at=timestamp,
        updated_at=timestamp,
        workspace_id=other_workspace,
    )
    with session_factory() as session:
        repository = SqlAlchemyKnowledgeRepository(session)
        repository.save(owned)
        repository.save(foreign)
        session.commit()
    with session_factory() as session:
        repository = SqlAlchemyKnowledgeRepository(session)
        assert repository.get_by_id(owned.id, workspace_id=other_workspace) is None
        assert repository.get_by_id(foreign.id, workspace_id=WorkspaceId.default()) is None
        assert [
            item.id for item in repository.list_by_workspace(workspace_id=WorkspaceId.default())
        ] == [owned.id]
        assert [item.id for item in repository.list_by_workspace(workspace_id=other_workspace)] == [
            foreign.id
        ]
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
        workspace_id=WorkspaceId.default(),
    )
    second = Chunk.create(
        document_id=DOCUMENT_ID,
        document_version_id=DOCUMENT_VERSION_ID,
        chunk_index=ChunkIndex(1),
        text="Second chunk.",
        knowledge_item_id=knowledge_item_id,
        workspace_id=WorkspaceId.default(),
    )
    with session_factory() as session:
        repository = SqlAlchemyChunkRepository(session)
        repository.save_many([first, second])
        session.commit()
    with session_factory() as session:
        repository = SqlAlchemyChunkRepository(session)
        loaded = repository.list_by_document_version(
            document_id=DOCUMENT_ID, document_version_id=DOCUMENT_VERSION_ID
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
        workspace_id=WorkspaceId.default(),
    )
    with session_factory() as session:
        repository = SqlAlchemyChunkRepository(session)
        repository.save_many([updated_second])
        session.commit()
    with session_factory() as session:
        repository = SqlAlchemyChunkRepository(session)
        loaded = repository.list_by_document_version(
            document_id=DOCUMENT_ID, document_version_id=DOCUMENT_VERSION_ID
        )
        assert loaded[1].text == "Updated second chunk."
        repository.delete_by_document_version(
            document_id=DOCUMENT_ID, document_version_id=DOCUMENT_VERSION_ID
        )
        session.commit()
    with session_factory() as session:
        repository = SqlAlchemyChunkRepository(session)
        assert (
            repository.list_by_document_version(
                document_id=DOCUMENT_ID, document_version_id=DOCUMENT_VERSION_ID
            )
            == []
        )
    engine.dispose()
