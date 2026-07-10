from datetime import UTC, datetime

import pytest
from memovi_search.domain.entities import Embedding, SearchDocument
from memovi_search.domain.exceptions import (
    InvalidDocumentReferenceError,
    InvalidEmbeddingError,
    InvalidKnowledgeItemReferenceError,
    InvalidSearchDocumentError,
)
from memovi_search.domain.value_objects import EmbeddingId, SearchDocumentId

DOCUMENT_ID = "3b96152e-5ba9-4933-8819-2a08069a6d9f"
DOCUMENT_VERSION_ID = "7ce3e814-de68-4200-973e-b2526eee058d"
KNOWLEDGE_ITEM_ID = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"


def test_search_document_create_assigns_identifiers_and_normalizes_text() -> None:
    timestamp = datetime(2026, 7, 10, 12, 0, tzinfo=UTC)
    search_document = SearchDocument.create(
        knowledge_item_id=KNOWLEDGE_ITEM_ID,
        document_id=DOCUMENT_ID,
        document_version_id=DOCUMENT_VERSION_ID,
        searchable_text="  Retrievable passage.  ",
        now=timestamp,
    )

    assert search_document.id.value
    assert search_document.knowledge_item_id == KNOWLEDGE_ITEM_ID
    assert search_document.searchable_text == "Retrievable passage."
    assert search_document.created_at == timestamp
    assert search_document.updated_at == timestamp


def test_search_document_touch_updates_only_updated_at() -> None:
    created_at = datetime(2026, 7, 10, 12, 0, tzinfo=UTC)
    updated_at = datetime(2026, 7, 10, 12, 5, tzinfo=UTC)
    search_document = SearchDocument(
        id=SearchDocumentId.new(),
        knowledge_item_id=KNOWLEDGE_ITEM_ID,
        document_id=DOCUMENT_ID,
        document_version_id=DOCUMENT_VERSION_ID,
        searchable_text="Stable text.",
        created_at=created_at,
        updated_at=updated_at,
    )

    touched = search_document.touch(datetime(2026, 7, 10, 13, 0, tzinfo=UTC))

    assert touched.created_at == created_at
    assert touched.updated_at == datetime(2026, 7, 10, 13, 0, tzinfo=UTC)
    assert touched.searchable_text == "Stable text."


def test_search_document_create_rejects_empty_searchable_text() -> None:
    with pytest.raises(InvalidSearchDocumentError):
        SearchDocument.create(
            knowledge_item_id=KNOWLEDGE_ITEM_ID,
            document_id=DOCUMENT_ID,
            document_version_id=DOCUMENT_VERSION_ID,
            searchable_text="   ",
        )


def test_search_document_rejects_invalid_document_reference() -> None:
    with pytest.raises(InvalidDocumentReferenceError):
        SearchDocument.create(
            knowledge_item_id=KNOWLEDGE_ITEM_ID,
            document_id="not-a-uuid",
            document_version_id=DOCUMENT_VERSION_ID,
            searchable_text="Valid text.",
        )


def test_search_document_rejects_invalid_knowledge_item_reference() -> None:
    with pytest.raises(InvalidKnowledgeItemReferenceError):
        SearchDocument.create(
            knowledge_item_id="invalid",
            document_id=DOCUMENT_ID,
            document_version_id=DOCUMENT_VERSION_ID,
            searchable_text="Valid text.",
        )


def test_search_document_rejects_updated_at_before_created_at() -> None:
    with pytest.raises(InvalidSearchDocumentError):
        SearchDocument(
            id=SearchDocumentId.new(),
            knowledge_item_id=KNOWLEDGE_ITEM_ID,
            document_id=DOCUMENT_ID,
            document_version_id=DOCUMENT_VERSION_ID,
            searchable_text="Valid text.",
            created_at=datetime(2026, 7, 10, 13, 0, tzinfo=UTC),
            updated_at=datetime(2026, 7, 10, 12, 0, tzinfo=UTC),
        )


def test_embedding_create_stores_vector_and_dimensions() -> None:
    search_document_id = SearchDocumentId.new()
    embedding = Embedding.create(
        search_document_id=search_document_id,
        provider="openai",
        model="text-embedding-3-small",
        vector=[0.1, 0.2, 0.3],
    )

    assert embedding.id.value
    assert embedding.search_document_id == search_document_id
    assert embedding.provider == "openai"
    assert embedding.model == "text-embedding-3-small"
    assert embedding.dimensions == 3
    assert embedding.vector == (0.1, 0.2, 0.3)


def test_embedding_create_trims_provider_and_model() -> None:
    embedding = Embedding.create(
        search_document_id=SearchDocumentId.new(),
        provider="  openai  ",
        model="  text-embedding-3-small  ",
        vector=[1.0],
    )

    assert embedding.provider == "openai"
    assert embedding.model == "text-embedding-3-small"


def test_embedding_rejects_empty_vector() -> None:
    with pytest.raises(InvalidEmbeddingError):
        Embedding.create(
            search_document_id=SearchDocumentId.new(),
            provider="openai",
            model="text-embedding-3-small",
            vector=[],
        )


def test_embedding_rejects_dimension_mismatch() -> None:
    with pytest.raises(InvalidEmbeddingError):
        Embedding(
            id=EmbeddingId.new(),
            search_document_id=SearchDocumentId.new(),
            provider="openai",
            model="text-embedding-3-small",
            dimensions=4,
            vector=(0.1, 0.2, 0.3),
        )


def test_embedding_rejects_empty_provider() -> None:
    with pytest.raises(InvalidEmbeddingError):
        Embedding.create(
            search_document_id=SearchDocumentId.new(),
            provider="   ",
            model="text-embedding-3-small",
            vector=[0.1],
        )
