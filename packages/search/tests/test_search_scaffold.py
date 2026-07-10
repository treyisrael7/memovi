from datetime import UTC, datetime

from memovi_search.application.dto import EmbeddingDto, SearchDocumentDto
from memovi_search.domain.entities import Embedding, SearchDocument
from memovi_search.infrastructure.persistence.models import (
    Base,
    SearchDocumentRecord,
    SearchEmbeddingRecord,
)

DOCUMENT_ID = "3b96152e-5ba9-4933-8819-2a08069a6d9f"
DOCUMENT_VERSION_ID = "7ce3e814-de68-4200-973e-b2526eee058d"
CHUNK_ID = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"


def test_dtos_map_from_domain_entities() -> None:
    search_document = SearchDocument.register(
        document_id=DOCUMENT_ID,
        document_version_id=DOCUMENT_VERSION_ID,
        chunk_id=CHUNK_ID,
    )
    embedding = Embedding.record(
        search_document_id=search_document.id,
        model_id="text-embedding-3-small",
        dimensions=1536,
    )

    search_document_dto = SearchDocumentDto.from_search_document(search_document)
    embedding_dto = EmbeddingDto.from_embedding(embedding)

    assert search_document_dto.id == search_document.id.value
    assert search_document_dto.chunk_id == CHUNK_ID
    assert embedding_dto.model_id == "text-embedding-3-small"
    assert embedding_dto.dimensions == 1536


def test_persistence_models_declare_expected_tables() -> None:
    assert SearchDocumentRecord.__tablename__ == "search_documents"
    assert SearchEmbeddingRecord.__tablename__ == "search_embeddings"
    assert Base.metadata.tables["search_documents"] is not None
    assert Base.metadata.tables["search_embeddings"] is not None


def test_domain_entities_enforce_invariants() -> None:
    timestamp = datetime(2026, 7, 10, 12, 0, tzinfo=UTC)
    search_document = SearchDocument(
        id=SearchDocument.register(
            document_id=DOCUMENT_ID,
            document_version_id=DOCUMENT_VERSION_ID,
            chunk_id=CHUNK_ID,
        ).id,
        document_id=DOCUMENT_ID,
        document_version_id=DOCUMENT_VERSION_ID,
        chunk_id=CHUNK_ID,
        created_at=timestamp,
        updated_at=timestamp,
    )

    assert search_document.created_at.tzinfo is UTC
