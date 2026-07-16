from datetime import UTC, datetime

from memovi_memory.application.dto import ChunkDto, KnowledgeDto, KnowledgeItemDto
from memovi_memory.domain.entities import Chunk, KnowledgeItem
from memovi_memory.domain.value_objects import ChunkIndex, KnowledgeItemId

DOCUMENT_ID = "d62fa912-48a9-4d57-abf2-40a137f48ffa"
DOCUMENT_VERSION_ID = "7d086319-ee8e-4fe5-9fc3-30eddad79749"
KNOWLEDGE_ITEM_ID = KnowledgeItemId("a1b2c3d4-e5f6-7890-abcd-ef1234567890")
TIMESTAMP = datetime(2026, 7, 10, 12, 0, tzinfo=UTC)
SOURCE_TYPE = "upload"
MIME_TYPE = "text/markdown"


def test_knowledge_item_dto_maps_domain_entity() -> None:
    knowledge_item = KnowledgeItem(
        id=KNOWLEDGE_ITEM_ID,
        document_id=DOCUMENT_ID,
        document_version_id=DOCUMENT_VERSION_ID,
        source_type=SOURCE_TYPE,
        mime_type=MIME_TYPE,
        created_at=TIMESTAMP,
        updated_at=TIMESTAMP,
    )

    dto = KnowledgeItemDto.from_knowledge_item(knowledge_item)

    assert dto.id == KNOWLEDGE_ITEM_ID.value
    assert dto.document_id == DOCUMENT_ID
    assert dto.document_version_id == DOCUMENT_VERSION_ID
    assert dto.created_at == TIMESTAMP
    assert dto.updated_at == TIMESTAMP


def test_chunk_dto_maps_domain_entity() -> None:
    chunk = Chunk.create(
        document_id=DOCUMENT_ID,
        document_version_id=DOCUMENT_VERSION_ID,
        chunk_index=ChunkIndex(1),
        text="  Canonical chunk text. ",
        knowledge_item_id=KNOWLEDGE_ITEM_ID,
        now=TIMESTAMP,
    )

    dto = ChunkDto.from_chunk(chunk)

    assert dto.id == chunk.id.value
    assert dto.knowledge_item_id == KNOWLEDGE_ITEM_ID.value
    assert dto.document_id == DOCUMENT_ID
    assert dto.document_version_id == DOCUMENT_VERSION_ID
    assert dto.chunk_index == 1
    assert dto.text == "Canonical chunk text."
    assert dto.created_at == TIMESTAMP


def test_knowledge_dto_maps_item_and_chunks_in_index_order() -> None:
    knowledge_item = KnowledgeItem(
        id=KNOWLEDGE_ITEM_ID,
        document_id=DOCUMENT_ID,
        document_version_id=DOCUMENT_VERSION_ID,
        source_type=SOURCE_TYPE,
        mime_type=MIME_TYPE,
        created_at=TIMESTAMP,
        updated_at=TIMESTAMP,
    )
    second_chunk = Chunk.create(
        document_id=DOCUMENT_ID,
        document_version_id=DOCUMENT_VERSION_ID,
        chunk_index=ChunkIndex(1),
        text="Second chunk.",
        knowledge_item_id=KNOWLEDGE_ITEM_ID,
        now=TIMESTAMP,
    )
    first_chunk = Chunk.create(
        document_id=DOCUMENT_ID,
        document_version_id=DOCUMENT_VERSION_ID,
        chunk_index=ChunkIndex(0),
        text="First chunk.",
        knowledge_item_id=KNOWLEDGE_ITEM_ID,
        now=TIMESTAMP,
    )

    dto = KnowledgeDto.from_knowledge_item_and_chunks(
        knowledge_item,
        [second_chunk, first_chunk],
    )

    assert dto.id == KNOWLEDGE_ITEM_ID.value
    assert dto.document_id == DOCUMENT_ID
    assert dto.document_version_id == DOCUMENT_VERSION_ID
    assert dto.created_at == TIMESTAMP
    assert dto.updated_at == TIMESTAMP
    assert len(dto.chunks) == 2
    assert dto.chunks[0].chunk_index == 0
    assert dto.chunks[0].text == "First chunk."
    assert dto.chunks[1].chunk_index == 1
    assert dto.chunks[1].text == "Second chunk."
