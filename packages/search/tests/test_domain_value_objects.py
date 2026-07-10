import uuid

import pytest
from memovi_search.domain.exceptions import InvalidEmbeddingIdError, InvalidSearchDocumentIdError
from memovi_search.domain.value_objects import EmbeddingId, SearchDocumentId


def test_search_document_id_normalizes_uuid_string() -> None:
    raw_id = str(uuid.uuid4())
    search_document_id = SearchDocumentId(raw_id.upper())

    assert search_document_id.value == raw_id
    assert str(search_document_id) == raw_id


def test_search_document_id_rejects_invalid_value() -> None:
    with pytest.raises(InvalidSearchDocumentIdError):
        SearchDocumentId("not-a-uuid")


def test_embedding_id_equality_uses_value_semantics() -> None:
    raw_id = str(uuid.uuid4())
    first = EmbeddingId(raw_id)
    second = EmbeddingId(raw_id)

    assert first == second
    assert hash(first) == hash(second)


def test_embedding_id_rejects_invalid_value() -> None:
    with pytest.raises(InvalidEmbeddingIdError):
        EmbeddingId("invalid")


def test_value_objects_are_immutable() -> None:
    search_document_id = SearchDocumentId.new()

    with pytest.raises(AttributeError):
        search_document_id.value = "changed"  # type: ignore[misc]
