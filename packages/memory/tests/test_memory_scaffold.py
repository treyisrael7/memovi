from memovi_memory.application.dto import ChunkDto, KnowledgeItemDto
from memovi_memory.domain.entities import Chunk, KnowledgeItem
from memovi_memory.domain.value_objects import ChunkIndex
from memovi_memory.infrastructure.persistence.models import (
    Base,
    ChunkRecord,
    KnowledgeItemRecord,
)

DOCUMENT_ID = "3b96152e-5ba9-4933-8819-2a08069a6d9f"
DOCUMENT_VERSION_ID = "7ce3e814-de68-4200-973e-b2526eee058d"


def test_dtos_map_from_domain_entities() -> None:
    knowledge_item = KnowledgeItem.create(
        document_id=DOCUMENT_ID,
        document_version_id=DOCUMENT_VERSION_ID,
    )
    chunk = Chunk.create(
        document_id=DOCUMENT_ID,
        document_version_id=DOCUMENT_VERSION_ID,
        chunk_index=ChunkIndex(1),
        text="Another passage.",
        knowledge_item_id=knowledge_item.id,
    )

    knowledge_item_dto = KnowledgeItemDto.from_knowledge_item(knowledge_item)
    chunk_dto = ChunkDto.from_chunk(chunk)

    assert knowledge_item_dto.id == knowledge_item.id.value
    assert chunk_dto.chunk_index == 1
    assert chunk_dto.text == "Another passage."


def test_persistence_models_declare_expected_tables() -> None:
    assert KnowledgeItemRecord.__tablename__ == "memory_knowledge_items"
    assert ChunkRecord.__tablename__ == "memory_chunks"
    assert Base.metadata.tables["memory_knowledge_items"] is not None
    assert Base.metadata.tables["memory_chunks"] is not None
