import builtins
from datetime import UTC, datetime

import pytest
from memovi_memory.application.exceptions import KnowledgeItemNotFoundError
from memovi_memory.application.queries import GetKnowledge, ListDocumentKnowledge, ListKnowledge
from memovi_memory.domain.entities import Chunk, KnowledgeItem
from memovi_memory.domain.repositories import ChunkRepository, KnowledgeRepository
from memovi_memory.domain.value_objects import ChunkIndex, KnowledgeItemId

DOCUMENT_A_ID = "d62fa912-48a9-4d57-abf2-40a137f48ffa"
DOCUMENT_B_ID = "8e1b0f2a-1c3d-4e5f-9a0b-1c2d3e4f5a6b"
VERSION_A1_ID = "7d086319-ee8e-4fe5-9fc3-30eddad79749"
VERSION_A2_ID = "9f086319-ee8e-4fe5-9fc3-30eddad79750"
KNOWLEDGE_A1_ID = KnowledgeItemId("a1b2c3d4-e5f6-7890-abcd-ef1234567890")
KNOWLEDGE_A2_ID = KnowledgeItemId("b2c3d4e5-f6a7-8901-bcde-f12345678901")
KNOWLEDGE_B1_ID = KnowledgeItemId("c3d4e5f6-a7b8-9012-cdef-123456789012")
EARLIER = datetime(2026, 7, 10, 10, 0, tzinfo=UTC)
LATER = datetime(2026, 7, 10, 11, 0, tzinfo=UTC)
SOURCE_TYPE = "upload"
MIME_TYPE = "text/markdown"


class InMemoryKnowledgeRepository(KnowledgeRepository):
    def __init__(self, items: list[KnowledgeItem]) -> None:
        self._items = items

    def save(self, knowledge_item: KnowledgeItem) -> None:
        raise NotImplementedError

    def get_by_id(self, knowledge_item_id: KnowledgeItemId) -> KnowledgeItem | None:
        for item in self._items:
            if item.id == knowledge_item_id:
                return item
        return None

    def list(self) -> builtins.list[KnowledgeItem]:
        return sorted(self._items, key=lambda item: item.created_at)

    def list_by_document(self, *, document_id: str) -> builtins.list[KnowledgeItem]:
        return sorted(
            [item for item in self._items if item.document_id == document_id],
            key=lambda item: item.created_at,
        )

    def list_by_document_version(
        self,
        *,
        document_id: str,
        document_version_id: str,
    ) -> builtins.list[KnowledgeItem]:
        return [
            item
            for item in self._items
            if item.document_id == document_id and item.document_version_id == document_version_id
        ]

    def delete(self, knowledge_item_id: KnowledgeItemId) -> None:
        raise NotImplementedError


class InMemoryChunkRepository(ChunkRepository):
    def __init__(self, chunks: list[Chunk]) -> None:
        self._chunks = chunks

    def save_many(self, chunks: list[Chunk]) -> None:
        raise NotImplementedError

    def list_by_document_version(
        self,
        *,
        document_id: str,
        document_version_id: str,
    ) -> list[Chunk]:
        return sorted(
            [
                chunk
                for chunk in self._chunks
                if chunk.document_id == document_id
                and chunk.document_version_id == document_version_id
            ],
            key=lambda chunk: chunk.chunk_index.value,
        )

    def delete_by_document_version(
        self,
        *,
        document_id: str,
        document_version_id: str,
    ) -> None:
        raise NotImplementedError


def _build_fixtures() -> tuple[InMemoryKnowledgeRepository, InMemoryChunkRepository]:
    knowledge_items = [
        KnowledgeItem(
            id=KNOWLEDGE_A1_ID,
            document_id=DOCUMENT_A_ID,
            document_version_id=VERSION_A1_ID,
            source_type=SOURCE_TYPE,
            mime_type=MIME_TYPE,
            created_at=EARLIER,
            updated_at=EARLIER,
        ),
        KnowledgeItem(
            id=KNOWLEDGE_A2_ID,
            document_id=DOCUMENT_A_ID,
            document_version_id=VERSION_A2_ID,
            source_type=SOURCE_TYPE,
            mime_type=MIME_TYPE,
            created_at=LATER,
            updated_at=LATER,
        ),
        KnowledgeItem(
            id=KNOWLEDGE_B1_ID,
            document_id=DOCUMENT_B_ID,
            document_version_id=VERSION_A1_ID,
            source_type=SOURCE_TYPE,
            mime_type=MIME_TYPE,
            created_at=LATER,
            updated_at=LATER,
        ),
    ]
    chunks = [
        Chunk.create(
            document_id=DOCUMENT_A_ID,
            document_version_id=VERSION_A1_ID,
            chunk_index=ChunkIndex(0),
            text="Document A version 1 chunk.",
            knowledge_item_id=KNOWLEDGE_A1_ID,
            now=EARLIER,
        ),
        Chunk.create(
            document_id=DOCUMENT_A_ID,
            document_version_id=VERSION_A2_ID,
            chunk_index=ChunkIndex(0),
            text="Document A version 2 chunk.",
            knowledge_item_id=KNOWLEDGE_A2_ID,
            now=LATER,
        ),
        Chunk.create(
            document_id=DOCUMENT_B_ID,
            document_version_id=VERSION_A1_ID,
            chunk_index=ChunkIndex(0),
            text="Document B chunk.",
            knowledge_item_id=KNOWLEDGE_B1_ID,
            now=LATER,
        ),
    ]
    return InMemoryKnowledgeRepository(knowledge_items), InMemoryChunkRepository(chunks)


def test_get_knowledge_returns_canonical_dto_with_chunks() -> None:
    knowledge_repository, chunk_repository = _build_fixtures()
    query = GetKnowledge(
        knowledge_repository=knowledge_repository,
        chunk_repository=chunk_repository,
    )

    result = query.execute(KNOWLEDGE_A1_ID.value)

    assert result.id == KNOWLEDGE_A1_ID.value
    assert result.document_id == DOCUMENT_A_ID
    assert result.document_version_id == VERSION_A1_ID
    assert len(result.chunks) == 1
    assert result.chunks[0].text == "Document A version 1 chunk."


def test_get_knowledge_raises_when_item_is_missing() -> None:
    knowledge_repository, chunk_repository = _build_fixtures()
    query = GetKnowledge(
        knowledge_repository=knowledge_repository,
        chunk_repository=chunk_repository,
    )

    with pytest.raises(KnowledgeItemNotFoundError):
        query.execute("00000000-0000-0000-0000-000000000000")


def test_list_knowledge_returns_all_items_in_created_at_order() -> None:
    knowledge_repository, chunk_repository = _build_fixtures()
    query = ListKnowledge(
        knowledge_repository=knowledge_repository,
        chunk_repository=chunk_repository,
    )

    results = query.execute()

    assert [item.id for item in results] == [
        KNOWLEDGE_A1_ID.value,
        KNOWLEDGE_A2_ID.value,
        KNOWLEDGE_B1_ID.value,
    ]
    assert all(len(item.chunks) == 1 for item in results)


def test_list_document_knowledge_returns_only_matching_document() -> None:
    knowledge_repository, chunk_repository = _build_fixtures()
    query = ListDocumentKnowledge(
        knowledge_repository=knowledge_repository,
        chunk_repository=chunk_repository,
    )

    results = query.execute(DOCUMENT_A_ID)

    assert [item.id for item in results] == [KNOWLEDGE_A1_ID.value, KNOWLEDGE_A2_ID.value]
    assert all(item.document_id == DOCUMENT_A_ID for item in results)
    assert results[0].chunks[0].text == "Document A version 1 chunk."
    assert results[1].chunks[0].text == "Document A version 2 chunk."


def test_list_document_knowledge_returns_empty_list_for_unknown_document() -> None:
    knowledge_repository, chunk_repository = _build_fixtures()
    query = ListDocumentKnowledge(
        knowledge_repository=knowledge_repository,
        chunk_repository=chunk_repository,
    )

    assert query.execute("00000000-0000-0000-0000-000000000000") == []
