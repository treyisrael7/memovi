from datetime import UTC, datetime

import pytest
from memovi_search.domain.entities import SearchDocument
from memovi_search.domain.exceptions import InvalidSearchMaterializationError
from memovi_search.domain.services import SearchMaterializer
from memovi_shared import WorkspaceId

DOCUMENT_ID = "3b96152e-5ba9-4933-8819-2a08069a6d9f"
DOCUMENT_VERSION_ID = "7ce3e814-de68-4200-973e-b2526eee058d"
KNOWLEDGE_ITEM_ID = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
SOURCE_TYPE = "upload"
MIME_TYPE = "text/markdown"
MATERIALIZED_AT = datetime(2026, 7, 10, 14, 0, tzinfo=UTC)


def _materializer() -> SearchMaterializer:
    return SearchMaterializer()


def test_search_materializer_creates_document_from_single_chunk() -> None:
    materializer = _materializer()

    search_document = materializer.materialize(
        workspace_id=WorkspaceId.default(),
        knowledge_item_id=KNOWLEDGE_ITEM_ID,
        document_id=DOCUMENT_ID,
        document_version_id=DOCUMENT_VERSION_ID,
        source_type=SOURCE_TYPE,
        mime_type=MIME_TYPE,
        chunk_texts=["First passage."],
        now=MATERIALIZED_AT,
    )

    assert isinstance(search_document, SearchDocument)
    assert search_document.searchable_text == "First passage."
    assert search_document.knowledge_item_id == KNOWLEDGE_ITEM_ID
    assert search_document.document_id == DOCUMENT_ID
    assert search_document.document_version_id == DOCUMENT_VERSION_ID
    assert search_document.created_at == MATERIALIZED_AT
    assert search_document.updated_at == MATERIALIZED_AT


def test_search_materializer_concatenates_multiple_chunks_in_order() -> None:
    materializer = _materializer()

    search_document = materializer.materialize(
        workspace_id=WorkspaceId.default(),
        knowledge_item_id=KNOWLEDGE_ITEM_ID,
        document_id=DOCUMENT_ID,
        document_version_id=DOCUMENT_VERSION_ID,
        source_type=SOURCE_TYPE,
        mime_type=MIME_TYPE,
        chunk_texts=["Alpha.", "Beta.", "Gamma."],
        now=MATERIALIZED_AT,
    )

    assert search_document.searchable_text == "Alpha.Beta.Gamma."


def test_search_materializer_normalizes_whitespace() -> None:
    materializer = _materializer()

    search_document = materializer.materialize(
        workspace_id=WorkspaceId.default(),
        knowledge_item_id=KNOWLEDGE_ITEM_ID,
        document_id=DOCUMENT_ID,
        document_version_id=DOCUMENT_VERSION_ID,
        source_type=SOURCE_TYPE,
        mime_type=MIME_TYPE,
        chunk_texts=["  Alpha   passage.  ", "\n\n", "  Beta\tpassage.  "],
        now=MATERIALIZED_AT,
    )

    assert search_document.searchable_text == "Alpha passage. Beta passage."


def test_search_materializer_rejects_empty_chunk_list() -> None:
    materializer = _materializer()

    with pytest.raises(InvalidSearchMaterializationError):
        materializer.materialize(
            workspace_id=WorkspaceId.default(),
            knowledge_item_id=KNOWLEDGE_ITEM_ID,
            document_id=DOCUMENT_ID,
            document_version_id=DOCUMENT_VERSION_ID,
            source_type=SOURCE_TYPE,
            mime_type=MIME_TYPE,
            chunk_texts=[],
            now=MATERIALIZED_AT,
        )


def test_search_materializer_rejects_whitespace_only_chunk_texts() -> None:
    materializer = _materializer()

    with pytest.raises(InvalidSearchMaterializationError):
        materializer.materialize(
            workspace_id=WorkspaceId.default(),
            knowledge_item_id=KNOWLEDGE_ITEM_ID,
            document_id=DOCUMENT_ID,
            document_version_id=DOCUMENT_VERSION_ID,
            source_type=SOURCE_TYPE,
            mime_type=MIME_TYPE,
            chunk_texts=["   ", "\n\t"],
            now=MATERIALIZED_AT,
        )


def test_search_materializer_is_deterministic_for_same_input() -> None:
    materializer = _materializer()
    chunk_texts = ["Alpha.", "Beta."]

    first = materializer.materialize(
        workspace_id=WorkspaceId.default(),
        knowledge_item_id=KNOWLEDGE_ITEM_ID,
        document_id=DOCUMENT_ID,
        document_version_id=DOCUMENT_VERSION_ID,
        source_type=SOURCE_TYPE,
        mime_type=MIME_TYPE,
        chunk_texts=chunk_texts,
        now=MATERIALIZED_AT,
    )
    second = materializer.materialize(
        workspace_id=WorkspaceId.default(),
        knowledge_item_id=KNOWLEDGE_ITEM_ID,
        document_id=DOCUMENT_ID,
        document_version_id=DOCUMENT_VERSION_ID,
        source_type=SOURCE_TYPE,
        mime_type=MIME_TYPE,
        chunk_texts=chunk_texts,
        now=MATERIALIZED_AT,
    )

    assert first == second
