import uuid

import pytest
from memovi_memory.domain.exceptions import (
    InvalidChunkIdError,
    InvalidChunkIndexError,
    InvalidKnowledgeItemIdError,
)
from memovi_memory.domain.value_objects import ChunkId, ChunkIndex, KnowledgeItemId


def test_knowledge_item_id_normalizes_uuid_string() -> None:
    raw_id = str(uuid.uuid4())
    knowledge_item_id = KnowledgeItemId(raw_id.upper())

    assert knowledge_item_id.value == raw_id
    assert str(knowledge_item_id) == raw_id


def test_knowledge_item_id_rejects_invalid_value() -> None:
    with pytest.raises(InvalidKnowledgeItemIdError):
        KnowledgeItemId("not-a-uuid")


def test_chunk_id_equality_uses_value_semantics() -> None:
    raw_id = str(uuid.uuid4())
    first = ChunkId(raw_id)
    second = ChunkId(raw_id)

    assert first == second
    assert hash(first) == hash(second)


def test_chunk_id_rejects_invalid_value() -> None:
    with pytest.raises(InvalidChunkIdError):
        ChunkId("invalid")


def test_chunk_index_accepts_zero() -> None:
    assert ChunkIndex(0).value == 0


def test_chunk_index_rejects_negative_values() -> None:
    with pytest.raises(InvalidChunkIndexError):
        ChunkIndex(-1)


def test_value_objects_are_immutable() -> None:
    chunk_index = ChunkIndex(2)

    with pytest.raises(AttributeError):
        chunk_index.value = 3  # type: ignore[misc]
