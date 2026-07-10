from datetime import UTC

from memovi_memory.application.dto import ChunkDto, KnowledgeItemDto
from memovi_memory.domain.entities import Chunk, KnowledgeItem
from memovi_memory.domain.value_objects import ChunkIndex
from memovi_memory.infrastructure.persistence.models import (
    Base,
    ChunkRecord,
    KnowledgeItemRecord,
)
from memovi_memory.infrastructure.repositories import (
    SqlAlchemyChunkRepository,
    SqlAlchemyKnowledgeRepository,
)
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


def test_domain_entities_can_be_created() -> None:
    knowledge_item = KnowledgeItem.create(
        document_id="3b96152e-5ba9-4933-8819-2a08069a6d9f",
        document_version_id="7ce3e814-de68-4200-973e-b2526eee058d",
    )
    chunk = Chunk.create(
        knowledge_item_id=knowledge_item.id,
        index=ChunkIndex(0),
        content="Retrievable passage.",
    )

    assert knowledge_item.id.value
    assert chunk.knowledge_item_id == knowledge_item.id


def test_dtos_map_from_domain_entities() -> None:
    knowledge_item = KnowledgeItem.create(
        document_id="3b96152e-5ba9-4933-8819-2a08069a6d9f",
        document_version_id="7ce3e814-de68-4200-973e-b2526eee058d",
    )
    chunk = Chunk.create(
        knowledge_item_id=knowledge_item.id,
        index=ChunkIndex(1),
        content="Another passage.",
    )

    knowledge_item_dto = KnowledgeItemDto.from_knowledge_item(knowledge_item)
    chunk_dto = ChunkDto.from_chunk(chunk)

    assert knowledge_item_dto.id == knowledge_item.id.value
    assert chunk_dto.index == 1


def test_persistence_models_declare_expected_tables() -> None:
    assert KnowledgeItemRecord.__tablename__ == "memory_knowledge_items"
    assert ChunkRecord.__tablename__ == "memory_chunks"
    assert Base.metadata.tables["memory_knowledge_items"] is not None
    assert Base.metadata.tables["memory_chunks"] is not None


def test_sqlalchemy_repositories_persist_and_load_entities() -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)

    with session_factory() as session:
        knowledge_repo = SqlAlchemyKnowledgeRepository(session)
        chunk_repo = SqlAlchemyChunkRepository(session)

        knowledge_item = KnowledgeItem.create(
            document_id="d62fa912-48a9-4d57-abf2-40a137f48ffa",
            document_version_id="7d086319-ee8e-4fe5-9fc3-30eddad79749",
        )
        chunk = Chunk.create(
            knowledge_item_id=knowledge_item.id,
            index=ChunkIndex(0),
            content="Mapped chunk content.",
        )

        knowledge_repo.add(knowledge_item)
        chunk_repo.add(chunk)
        session.commit()

    with session_factory() as session:
        knowledge_repo = SqlAlchemyKnowledgeRepository(session)
        chunk_repo = SqlAlchemyChunkRepository(session)

        loaded_item = knowledge_repo.get_by_id(knowledge_item.id)
        loaded_chunks = chunk_repo.list_by_knowledge_item_id(knowledge_item.id)

        assert loaded_item is not None
        assert loaded_item.document_id == knowledge_item.document_id
        assert loaded_item.created_at.tzinfo is UTC
        assert len(loaded_chunks) == 1
        assert loaded_chunks[0].content == "Mapped chunk content."

        record = session.scalar(select(ChunkRecord))
        assert record is not None
        assert record.chunk_index == 0

    engine.dispose()
