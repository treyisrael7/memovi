from datetime import UTC, datetime

from memovi_search.domain.entities import Embedding, SearchDocument
from memovi_search.domain.value_objects import EmbeddingId, SearchDocumentId
from memovi_search.infrastructure.persistence.models import (
    SearchDocumentRecord,
    SearchEmbeddingRecord,
)
from memovi_search.infrastructure.repositories.sqlalchemy_search_repository import (
    SqlAlchemySearchRepository,
)

DOCUMENT_ID = "d62fa912-48a9-4d57-abf2-40a137f48ffa"
DOCUMENT_VERSION_ID = "7d086319-ee8e-4fe5-9fc3-30eddad79749"
KNOWLEDGE_ITEM_ID = "f1e2d3c4-b5a6-9788-7654-3210fedcba98"


def test_document_mapping_round_trips_between_domain_and_record() -> None:
    repository = SqlAlchemySearchRepository(session=object())  # type: ignore[arg-type]
    timestamp = datetime(2026, 7, 10, 12, 0, tzinfo=UTC)
    search_document = SearchDocument(
        id=SearchDocumentId.new(),
        knowledge_item_id=KNOWLEDGE_ITEM_ID,
        document_id=DOCUMENT_ID,
        document_version_id=DOCUMENT_VERSION_ID,
        searchable_text="Retrievable passage.",
        created_at=timestamp,
        updated_at=timestamp,
    )

    record = repository._document_to_record(search_document)
    restored = repository._document_to_domain(record)

    assert isinstance(record, SearchDocumentRecord)
    assert record.knowledge_item_id == KNOWLEDGE_ITEM_ID
    assert record.searchable_text == "Retrievable passage."
    assert restored == search_document
    assert restored.created_at.tzinfo is UTC


def test_embedding_mapping_round_trips_between_domain_and_record() -> None:
    repository = SqlAlchemySearchRepository(session=object())  # type: ignore[arg-type]
    search_document_id = SearchDocumentId.new()
    embedding = Embedding(
        id=EmbeddingId.new(),
        search_document_id=search_document_id,
        provider="openai",
        model="text-embedding-3-small",
        dimensions=3,
        vector=(0.1, 0.2, 0.3),
    )

    record = repository._embedding_to_record(embedding)
    restored = repository._embedding_to_domain(record)

    assert isinstance(record, SearchEmbeddingRecord)
    assert record.provider == "openai"
    assert record.model == "text-embedding-3-small"
    assert record.vector == [0.1, 0.2, 0.3]
    assert restored == embedding
