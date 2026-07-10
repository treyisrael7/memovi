from datetime import UTC, datetime

import pytest
from memovi_memory.domain.exceptions import InvalidKnowledgeMaterializationError
from memovi_memory.domain.services import (
    ChunkDraft,
    KnowledgeMaterializer,
)
from memovi_memory.domain.value_objects import ChunkIndex

DOCUMENT_ID = "3b96152e-5ba9-4933-8819-2a08069a6d9f"
DOCUMENT_VERSION_ID = "7ce3e814-de68-4200-973e-b2526eee058d"
MATERIALIZED_AT = datetime(2026, 7, 9, 22, 30, tzinfo=UTC)


def _materializer() -> KnowledgeMaterializer:
    return KnowledgeMaterializer()


def test_knowledge_materializer_creates_single_chunk() -> None:
    materializer = _materializer()
    drafts = [ChunkDraft(chunk_index=ChunkIndex(0), text="First passage.")]

    result = materializer.materialize(
        document_id=DOCUMENT_ID,
        document_version_id=DOCUMENT_VERSION_ID,
        chunk_drafts=drafts,
        now=MATERIALIZED_AT,
    )

    assert len(result.chunks) == 1
    assert result.chunks[0].text == "First passage."
    assert result.chunks[0].chunk_index.value == 0


def test_knowledge_materializer_creates_multiple_chunks() -> None:
    materializer = _materializer()
    drafts = [
        ChunkDraft(chunk_index=ChunkIndex(0), text="Alpha."),
        ChunkDraft(chunk_index=ChunkIndex(1), text="Beta."),
        ChunkDraft(chunk_index=ChunkIndex(2), text="Gamma."),
    ]

    result = materializer.materialize(
        document_id=DOCUMENT_ID,
        document_version_id=DOCUMENT_VERSION_ID,
        chunk_drafts=drafts,
        now=MATERIALIZED_AT,
    )

    assert len(result.chunks) == 3
    assert [chunk.text for chunk in result.chunks] == ["Alpha.", "Beta.", "Gamma."]


def test_knowledge_materializer_rejects_empty_chunk_list() -> None:
    materializer = _materializer()

    with pytest.raises(InvalidKnowledgeMaterializationError):
        materializer.materialize(
            document_id=DOCUMENT_ID,
            document_version_id=DOCUMENT_VERSION_ID,
            chunk_drafts=[],
            now=MATERIALIZED_AT,
        )


def test_knowledge_materializer_assigns_chunk_ownership_to_knowledge_item() -> None:
    materializer = _materializer()
    drafts = [
        ChunkDraft(chunk_index=ChunkIndex(0), text="Owned passage."),
        ChunkDraft(chunk_index=ChunkIndex(1), text="Another owned passage."),
    ]

    result = materializer.materialize(
        document_id=DOCUMENT_ID,
        document_version_id=DOCUMENT_VERSION_ID,
        chunk_drafts=drafts,
        now=MATERIALIZED_AT,
    )

    for chunk in result.chunks:
        assert chunk.knowledge_item_id == result.knowledge_item.id


def test_knowledge_materializer_preserves_sequential_chunk_indexes() -> None:
    materializer = _materializer()
    drafts = [
        ChunkDraft(chunk_index=ChunkIndex(0), text="One."),
        ChunkDraft(chunk_index=ChunkIndex(1), text="Two."),
        ChunkDraft(chunk_index=ChunkIndex(2), text="Three."),
    ]

    result = materializer.materialize(
        document_id=DOCUMENT_ID,
        document_version_id=DOCUMENT_VERSION_ID,
        chunk_drafts=drafts,
        now=MATERIALIZED_AT,
    )

    assert [chunk.chunk_index.value for chunk in result.chunks] == [0, 1, 2]


def test_knowledge_materializer_propagates_document_identifiers() -> None:
    materializer = _materializer()
    drafts = [ChunkDraft(chunk_index=ChunkIndex(0), text="Propagated.")]

    result = materializer.materialize(
        document_id=DOCUMENT_ID,
        document_version_id=DOCUMENT_VERSION_ID,
        chunk_drafts=drafts,
        now=MATERIALIZED_AT,
    )

    assert result.knowledge_item.document_id == DOCUMENT_ID
    assert result.knowledge_item.document_version_id == DOCUMENT_VERSION_ID
    assert result.chunks[0].document_id == DOCUMENT_ID
    assert result.chunks[0].document_version_id == DOCUMENT_VERSION_ID


def test_knowledge_materializer_is_deterministic_for_same_input() -> None:
    materializer = _materializer()
    drafts = [
        ChunkDraft(chunk_index=ChunkIndex(0), text="Deterministic."),
        ChunkDraft(chunk_index=ChunkIndex(1), text="Output."),
    ]

    first = materializer.materialize(
        document_id=DOCUMENT_ID,
        document_version_id=DOCUMENT_VERSION_ID,
        chunk_drafts=drafts,
        now=MATERIALIZED_AT,
    )
    second = materializer.materialize(
        document_id=DOCUMENT_ID,
        document_version_id=DOCUMENT_VERSION_ID,
        chunk_drafts=drafts,
        now=MATERIALIZED_AT,
    )

    assert first == second
