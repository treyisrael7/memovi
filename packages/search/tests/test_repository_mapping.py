from datetime import UTC, datetime

from memovi_search.domain.entities import Embedding, SearchDocument
from memovi_search.domain.value_objects import EmbeddingId, SearchDocumentId
from memovi_search.infrastructure.persistence.models import (
    SearchDocumentRecord,
    SearchEmbeddingRecord,
)
from memovi_search.infrastructure.repositories.sqlalchemy_embedding_repository import (
    SqlAlchemyEmbeddingRepository,
)
from memovi_search.infrastructure.repositories.sqlalchemy_search_repository import (
    SqlAlchemySearchRepository,
)
from memovi_shared import WorkspaceId

DOCUMENT_ID = "d62fa912-48a9-4d57-abf2-40a137f48ffa"
DOCUMENT_VERSION_ID = "7d086319-ee8e-4fe5-9fc3-30eddad79749"
KNOWLEDGE_ITEM_ID = "f1e2d3c4-b5a6-9788-7654-3210fedcba98"
SOURCE_TYPE = "upload"
MIME_TYPE = "text/markdown"


def test_document_mapping_round_trips_between_domain_and_record() -> None:
    repository = SqlAlchemySearchRepository(session=object())
    timestamp = datetime(2026, 7, 10, 12, 0, tzinfo=UTC)
    search_document = SearchDocument(
        id=SearchDocumentId.new(),
        knowledge_item_id=KNOWLEDGE_ITEM_ID,
        document_id=DOCUMENT_ID,
        document_version_id=DOCUMENT_VERSION_ID,
        source_type=SOURCE_TYPE,
        mime_type=MIME_TYPE,
        searchable_text="Retrievable passage.",
        created_at=timestamp,
        updated_at=timestamp,
        workspace_id=WorkspaceId.default(),
    )
    record = repository._document_to_record(search_document)
    restored = repository._document_to_domain(record)
    assert isinstance(record, SearchDocumentRecord)
    assert record.knowledge_item_id == KNOWLEDGE_ITEM_ID
    assert record.searchable_text == "Retrievable passage."
    assert restored == search_document
    assert restored.created_at.tzinfo is UTC


def test_embedding_mapping_round_trips_between_domain_and_record() -> None:
    repository = SqlAlchemyEmbeddingRepository(session=object())
    search_document_id = SearchDocumentId.new()
    embedding = Embedding(
        id=EmbeddingId.new(),
        search_document_id=search_document_id,
        provider="openai",
        model="text-embedding-3-small",
        dimensions=4,
        vector=(0.1, 0.2, 0.3, 0.4),
    )
    record = repository._to_record(embedding)
    restored = repository._to_domain(record)
    assert isinstance(record, SearchEmbeddingRecord)
    assert record.provider == "openai"
    assert record.model == "text-embedding-3-small"
    assert record.vector == [0.1, 0.2, 0.3, 0.4]
    assert restored == embedding


def test_search_and_embedding_repositories_sqlite_crud() -> None:
    from memovi_search.domain.value_objects import EmbeddingVector
    from memovi_search.infrastructure.persistence.models import Base
    from memovi_search.infrastructure.persistence.vector import EMBEDDING_VECTOR_DIMENSIONS
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)

    doc_id = SearchDocumentId.new()
    timestamp = datetime(2026, 7, 10, 12, 0, tzinfo=UTC)
    search_document = SearchDocument(
        id=doc_id,
        knowledge_item_id=KNOWLEDGE_ITEM_ID,
        document_id=DOCUMENT_ID,
        document_version_id=DOCUMENT_VERSION_ID,
        source_type=SOURCE_TYPE,
        mime_type=MIME_TYPE,
        searchable_text="Retrievable passage in SQLite.",
        created_at=timestamp,
        updated_at=timestamp,
        workspace_id=WorkspaceId.default(),
    )

    with session_factory() as session:
        search_repo = SqlAlchemySearchRepository(session)
        search_repo.save_document(search_document)
        session.commit()

    with session_factory() as session:
        search_repo = SqlAlchemySearchRepository(session)
        loaded = search_repo.get_document(doc_id, workspace_id=WorkspaceId.default())
        assert loaded is not None
        assert loaded.searchable_text == "Retrievable passage in SQLite."

        listed = search_repo.list_documents(workspace_id=WorkspaceId.default())
        assert len(listed) == 1
        assert listed[0].id == doc_id

        # Update existing
        updated_doc = SearchDocument(
            id=doc_id,
            knowledge_item_id=KNOWLEDGE_ITEM_ID,
            document_id=DOCUMENT_ID,
            document_version_id=DOCUMENT_VERSION_ID,
            source_type=SOURCE_TYPE,
            mime_type=MIME_TYPE,
            searchable_text="Updated passage.",
            created_at=timestamp,
            updated_at=datetime(2026, 7, 10, 13, 0, tzinfo=UTC),
            workspace_id=WorkspaceId.default(),
        )
        search_repo.save_document(updated_doc)
        session.commit()

    with session_factory() as session:
        search_repo = SqlAlchemySearchRepository(session)
        loaded = search_repo.get_document(doc_id)
        assert loaded is not None
        assert loaded.searchable_text == "Updated passage."

        # Search returns empty without error on SQLite fallback
        assert (
            search_repo.search("test", limit=10, offset=0, workspace_id=WorkspaceId.default()) == []
        )

    # Embedding repository tests
    emb_id = EmbeddingId.new()
    vector_values = [0.1] * EMBEDDING_VECTOR_DIMENSIONS
    embedding = Embedding(
        id=emb_id,
        search_document_id=doc_id,
        provider="fake",
        model="fake-embedding-v1",
        dimensions=EMBEDDING_VECTOR_DIMENSIONS,
        vector=tuple(vector_values),
    )

    with session_factory() as session:
        emb_repo = SqlAlchemyEmbeddingRepository(session)
        emb_repo.save(embedding)
        session.commit()

    with session_factory() as session:
        emb_repo = SqlAlchemyEmbeddingRepository(session)
        loaded_emb = emb_repo.get_by_search_document(doc_id)
        assert loaded_emb is not None
        assert loaded_emb.id == emb_id
        assert loaded_emb.dimensions == EMBEDDING_VECTOR_DIMENSIONS

        # Update existing embedding via save
        updated_emb = Embedding(
            id=emb_id,
            search_document_id=doc_id,
            provider="fake",
            model="fake-embedding-v1",
            dimensions=EMBEDDING_VECTOR_DIMENSIONS,
            vector=tuple([0.2] * EMBEDDING_VECTOR_DIMENSIONS),
        )
        emb_repo.save(updated_emb)
        session.commit()

    with session_factory() as session:
        emb_repo = SqlAlchemyEmbeddingRepository(session)
        loaded_emb = emb_repo.get_by_search_document(doc_id)
        assert loaded_emb is not None
        assert loaded_emb.vector[0] == 0.2

        # Similarity search on SQLite returns empty list
        q_vec = EmbeddingVector(values=vector_values, dimensions=EMBEDDING_VECTOR_DIMENSIONS)
        assert emb_repo.similarity_search(q_vec, limit=5, workspace_id=WorkspaceId.default()) == []
        assert emb_repo.similarity_search(q_vec, limit=0, workspace_id=WorkspaceId.default()) == []

        emb_repo.delete(emb_id)
        session.commit()

    with session_factory() as session:
        emb_repo = SqlAlchemyEmbeddingRepository(session)
        assert emb_repo.get_by_search_document(doc_id) is None

        search_repo = SqlAlchemySearchRepository(session)
        search_repo.delete_document(doc_id, workspace_id=WorkspaceId.default())
        session.commit()

    with session_factory() as session:
        search_repo = SqlAlchemySearchRepository(session)
        assert search_repo.get_document(doc_id) is None

    engine.dispose()
