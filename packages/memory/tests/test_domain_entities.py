from datetime import UTC, datetime

import pytest
from memovi_memory.domain.entities import Chunk, KnowledgeItem
from memovi_memory.domain.exceptions import (
    InvalidChunkError,
    InvalidChunkIndexError,
    InvalidDocumentReferenceError,
    InvalidKnowledgeItemError,
)
from memovi_memory.domain.value_objects import ChunkIndex, KnowledgeItemId

DOCUMENT_ID = "3b96152e-5ba9-4933-8819-2a08069a6d9f"
DOCUMENT_VERSION_ID = "7ce3e814-de68-4200-973e-b2526eee058d"


def test_knowledge_item_create_assigns_identifiers_and_timestamps() -> None:
    timestamp = datetime(2026, 7, 9, 12, 0, tzinfo=UTC)
    knowledge_item = KnowledgeItem.create(
        document_id=DOCUMENT_ID,
        document_version_id=DOCUMENT_VERSION_ID,
        now=timestamp,
    )

    assert knowledge_item.id.value
    assert knowledge_item.document_id == DOCUMENT_ID
    assert knowledge_item.document_version_id == DOCUMENT_VERSION_ID
    assert knowledge_item.created_at == timestamp
    assert knowledge_item.updated_at == timestamp


def test_knowledge_item_touch_updates_only_updated_at() -> None:
    created_at = datetime(2026, 7, 9, 12, 0, tzinfo=UTC)
    updated_at = datetime(2026, 7, 9, 12, 5, tzinfo=UTC)
    knowledge_item = KnowledgeItem(
        id=KnowledgeItemId.new(),
        document_id=DOCUMENT_ID,
        document_version_id=DOCUMENT_VERSION_ID,
        created_at=created_at,
        updated_at=updated_at,
    )

    touched = knowledge_item.touch(datetime(2026, 7, 9, 13, 0, tzinfo=UTC))

    assert touched.created_at == created_at
    assert touched.updated_at == datetime(2026, 7, 9, 13, 0, tzinfo=UTC)


def test_knowledge_item_rejects_invalid_document_reference() -> None:
    with pytest.raises(InvalidDocumentReferenceError):
        KnowledgeItem.create(
            document_id="not-a-uuid",
            document_version_id=DOCUMENT_VERSION_ID,
        )


def test_knowledge_item_rejects_updated_at_before_created_at() -> None:
    with pytest.raises(InvalidKnowledgeItemError):
        KnowledgeItem(
            id=KnowledgeItemId.new(),
            document_id=DOCUMENT_ID,
            document_version_id=DOCUMENT_VERSION_ID,
            created_at=datetime(2026, 7, 9, 13, 0, tzinfo=UTC),
            updated_at=datetime(2026, 7, 9, 12, 0, tzinfo=UTC),
        )


def test_chunk_create_trims_text_and_preserves_document_references() -> None:
    chunk = Chunk.create(
        document_id=DOCUMENT_ID,
        document_version_id=DOCUMENT_VERSION_ID,
        chunk_index=ChunkIndex(0),
        text="  Retrievable passage.  ",
    )

    assert chunk.text == "Retrievable passage."
    assert chunk.document_id == DOCUMENT_ID
    assert chunk.document_version_id == DOCUMENT_VERSION_ID
    assert chunk.knowledge_item_id is None


def test_chunk_create_accepts_optional_knowledge_item_id() -> None:
    knowledge_item_id = KnowledgeItemId.new()
    chunk = Chunk.create(
        document_id=DOCUMENT_ID,
        document_version_id=DOCUMENT_VERSION_ID,
        chunk_index=ChunkIndex(1),
        text="Linked chunk.",
        knowledge_item_id=knowledge_item_id,
    )

    assert chunk.knowledge_item_id == knowledge_item_id


def test_chunk_create_rejects_empty_text() -> None:
    with pytest.raises(InvalidChunkError):
        Chunk.create(
            document_id=DOCUMENT_ID,
            document_version_id=DOCUMENT_VERSION_ID,
            chunk_index=ChunkIndex(0),
            text="   ",
        )


def test_chunk_create_rejects_invalid_chunk_index() -> None:
    with pytest.raises(InvalidChunkIndexError):
        Chunk.create(
            document_id=DOCUMENT_ID,
            document_version_id=DOCUMENT_VERSION_ID,
            chunk_index=ChunkIndex(-1),
            text="Invalid index.",
        )


def test_chunk_rejects_invalid_document_reference() -> None:
    with pytest.raises(InvalidDocumentReferenceError):
        Chunk.create(
            document_id=DOCUMENT_ID,
            document_version_id="invalid",
            chunk_index=ChunkIndex(0),
            text="Broken reference.",
        )
