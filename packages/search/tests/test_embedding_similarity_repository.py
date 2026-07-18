from memovi_shared import WorkspaceId
from datetime import UTC, datetime
import pytest
from memovi_search.domain.entities import Embedding, SearchDocument
from memovi_search.domain.value_objects import EmbeddingId, EmbeddingVector, SearchDocumentId
from memovi_search.infrastructure.persistence.vector import EMBEDDING_VECTOR_DIMENSIONS
from memovi_search.infrastructure.repositories import SqlAlchemyEmbeddingRepository, SqlAlchemySearchRepository
from postgres_support import build_postgres_session_factory, requires_postgres
DOCUMENT_ID = 'd62fa912-48a9-4d57-abf2-40a137f48ffa'
DOCUMENT_VERSION_ID = '7d086319-ee8e-4fe5-9fc3-30eddad79749'
KNOWLEDGE_NEAR = 'f1e2d3c4-b5a6-9788-7654-3210fedcba98'
KNOWLEDGE_MID = 'a1b2c3d4-e5f6-7890-abcd-ef1234567890'
KNOWLEDGE_FAR = 'b2c3d4e5-f6a7-8901-bcde-f12345678901'
SOURCE_TYPE = 'upload'
MIME_TYPE = 'text/markdown'
CREATED_AT = datetime(2026, 7, 13, 12, 0, tzinfo=UTC)
QUERY_VECTOR = [1.0, 0.0, 0.0, 0.0]
NEAR_VECTOR = [1.0, 0.0, 0.0, 0.0]
MID_VECTOR = [0.0, 1.0, 0.0, 0.0]
FAR_VECTOR = [-1.0, 0.0, 0.0, 0.0]

def _build_search_document(*, knowledge_item_id: str, searchable_text: str) -> SearchDocument:
    return SearchDocument(id=SearchDocumentId.new(), knowledge_item_id=knowledge_item_id, document_id=DOCUMENT_ID, document_version_id=DOCUMENT_VERSION_ID, source_type=SOURCE_TYPE, mime_type=MIME_TYPE, searchable_text=searchable_text, created_at=CREATED_AT, updated_at=CREATED_AT, workspace_id=WorkspaceId.default())

def _build_embedding(*, search_document_id: SearchDocumentId, vector: list[float]) -> Embedding:
    return Embedding(id=EmbeddingId.new(), search_document_id=search_document_id, provider='fake', model='fake-embedding-v1', dimensions=EMBEDDING_VECTOR_DIMENSIONS, vector=tuple(vector))

@requires_postgres
def test_similarity_search_returns_nearest_neighbors_ordered_by_cosine_similarity() -> None:
    session_factory, engine = build_postgres_session_factory()
    near_document = _build_search_document(knowledge_item_id=KNOWLEDGE_NEAR, searchable_text='Near neighbor document.')
    mid_document = _build_search_document(knowledge_item_id=KNOWLEDGE_MID, searchable_text='Mid neighbor document.')
    far_document = _build_search_document(knowledge_item_id=KNOWLEDGE_FAR, searchable_text='Far neighbor document.')
    with session_factory() as session:
        search_repository = SqlAlchemySearchRepository(session)
        embedding_repository = SqlAlchemyEmbeddingRepository(session)
        for document in (near_document, mid_document, far_document):
            search_repository.save_document(document)
        embedding_repository.save(_build_embedding(search_document_id=near_document.id, vector=NEAR_VECTOR))
        embedding_repository.save(_build_embedding(search_document_id=mid_document.id, vector=MID_VECTOR))
        embedding_repository.save(_build_embedding(search_document_id=far_document.id, vector=FAR_VECTOR))
        session.commit()
    query = EmbeddingVector(values=list(QUERY_VECTOR), dimensions=EMBEDDING_VECTOR_DIMENSIONS)
    with session_factory() as session:
        embedding_repository = SqlAlchemyEmbeddingRepository(session)
        results = embedding_repository.similarity_search(query, limit=3, workspace_id=WorkspaceId.default())
        assert [result.search_document.knowledge_item_id for result in results] == [KNOWLEDGE_NEAR, KNOWLEDGE_MID, KNOWLEDGE_FAR]
        assert results[0].relevance_score > results[1].relevance_score
        assert results[1].relevance_score > results[2].relevance_score
        assert results[0].relevance_score == pytest.approx(1.0, abs=1e-06)
        assert results[1].relevance_score == pytest.approx(0.0, abs=1e-06)
        assert results[2].relevance_score == pytest.approx(-1.0, abs=1e-06)
    engine.dispose()

@requires_postgres
def test_similarity_search_respects_limit() -> None:
    session_factory, engine = build_postgres_session_factory()
    near_document = _build_search_document(knowledge_item_id=KNOWLEDGE_NEAR, searchable_text='Near neighbor document.')
    mid_document = _build_search_document(knowledge_item_id=KNOWLEDGE_MID, searchable_text='Mid neighbor document.')
    with session_factory() as session:
        search_repository = SqlAlchemySearchRepository(session)
        embedding_repository = SqlAlchemyEmbeddingRepository(session)
        search_repository.save_document(near_document)
        search_repository.save_document(mid_document)
        embedding_repository.save(_build_embedding(search_document_id=near_document.id, vector=NEAR_VECTOR))
        embedding_repository.save(_build_embedding(search_document_id=mid_document.id, vector=MID_VECTOR))
        session.commit()
    query = EmbeddingVector(values=list(QUERY_VECTOR), dimensions=EMBEDDING_VECTOR_DIMENSIONS)
    with session_factory() as session:
        embedding_repository = SqlAlchemyEmbeddingRepository(session)
        results = embedding_repository.similarity_search(query, limit=1, workspace_id=WorkspaceId.default())
        assert len(results) == 1
        assert results[0].search_document.knowledge_item_id == KNOWLEDGE_NEAR
    engine.dispose()
