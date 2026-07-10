from datetime import UTC, datetime

from memovi_search.domain.entities import Embedding, SearchDocument
from memovi_search.domain.value_objects import EmbeddingId, SearchDocumentId
from memovi_search.infrastructure.persistence.models import Base
from memovi_search.infrastructure.repositories import SqlAlchemySearchRepository
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

DOCUMENT_ID = "d62fa912-48a9-4d57-abf2-40a137f48ffa"
DOCUMENT_VERSION_ID = "7d086319-ee8e-4fe5-9fc3-30eddad79749"
CHUNK_ID = "f1e2d3c4-b5a6-9788-7654-3210fedcba98"


def _build_session_factory() -> tuple[sessionmaker[Session], Engine]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False), engine


def test_search_repository_round_trips_search_documents_and_embeddings() -> None:
    session_factory, engine = _build_session_factory()
    timestamp = datetime(2026, 7, 10, 12, 0, tzinfo=UTC)
    search_document = SearchDocument(
        id=SearchDocumentId.new(),
        document_id=DOCUMENT_ID,
        document_version_id=DOCUMENT_VERSION_ID,
        chunk_id=CHUNK_ID,
        created_at=timestamp,
        updated_at=timestamp,
    )
    embedding = Embedding(
        id=EmbeddingId.new(),
        search_document_id=search_document.id,
        model_id="text-embedding-3-small",
        dimensions=1536,
        created_at=timestamp,
    )

    with session_factory() as session:
        repository = SqlAlchemySearchRepository(session)
        repository.save_search_document(search_document)
        repository.save_embedding(embedding)
        session.commit()

    with session_factory() as session:
        repository = SqlAlchemySearchRepository(session)
        loaded_document = repository.get_search_document(search_document.id)
        loaded_embeddings = repository.list_embeddings_for_search_document(
            search_document_id=search_document.id,
        )
        documents_for_chunk = repository.list_search_documents_by_chunk(chunk_id=CHUNK_ID)

        assert loaded_document is not None
        assert loaded_document.document_id == DOCUMENT_ID
        assert loaded_document.created_at.tzinfo is UTC
        assert len(documents_for_chunk) == 1
        assert len(loaded_embeddings) == 1
        assert loaded_embeddings[0].model_id == "text-embedding-3-small"

    updated = search_document.touch(datetime(2026, 7, 10, 12, 30, tzinfo=UTC))
    with session_factory() as session:
        repository = SqlAlchemySearchRepository(session)
        repository.save_search_document(updated)
        session.commit()

    with session_factory() as session:
        repository = SqlAlchemySearchRepository(session)
        loaded_document = repository.get_search_document(search_document.id)
        assert loaded_document is not None
        assert loaded_document.updated_at == datetime(2026, 7, 10, 12, 30, tzinfo=UTC)

        repository.delete_embedding(embedding.id)
        repository.delete_search_document(search_document.id)
        session.commit()

    with session_factory() as session:
        repository = SqlAlchemySearchRepository(session)
        assert repository.get_search_document(search_document.id) is None
        assert repository.get_embedding(embedding.id) is None
        assert repository.list_search_documents_by_document(document_id=DOCUMENT_ID) == []

    engine.dispose()
