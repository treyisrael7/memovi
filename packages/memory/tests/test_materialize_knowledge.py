from datetime import datetime
from typing import cast

import pytest
from memovi_memory.application.commands import (
    MaterializeKnowledge,
    MaterializeKnowledgeCommand,
)
from memovi_memory.application.exceptions import NoChunksGeneratedError
from memovi_memory.domain.entities import Chunk, KnowledgeItem
from memovi_memory.domain.repositories import ChunkRepository, KnowledgeRepository
from memovi_memory.domain.services import (
    ChunkDraft,
    ChunkGenerator,
    KnowledgeMaterializationResult,
    KnowledgeMaterializer,
)
from memovi_memory.domain.value_objects import KnowledgeItemId

DOCUMENT_ID = "3b96152e-5ba9-4933-8819-2a08069a6d9f"
DOCUMENT_VERSION_ID = "7ce3e814-de68-4200-973e-b2526eee058d"
MAX_CHUNK_SIZE = 20


class FakeKnowledgeRepository(KnowledgeRepository):
    def __init__(self, operations: list[str]) -> None:
        self._operations = operations
        self.saved_items: list[KnowledgeItem] = []

    def save(self, knowledge_item: KnowledgeItem) -> None:
        self._operations.append("knowledge_save")
        self.saved_items.append(knowledge_item)

    def get_by_id(self, knowledge_item_id: KnowledgeItemId) -> KnowledgeItem | None:
        for item in self.saved_items:
            if item.id == knowledge_item_id:
                return item
        return None

    def list_by_document_version(
        self,
        *,
        document_id: str,
        document_version_id: str,
    ) -> list[KnowledgeItem]:
        return [
            item
            for item in self.saved_items
            if item.document_id == document_id and item.document_version_id == document_version_id
        ]

    def delete(self, knowledge_item_id: KnowledgeItemId) -> None:
        self.saved_items = [item for item in self.saved_items if item.id != knowledge_item_id]


class FakeChunkRepository(ChunkRepository):
    def __init__(self, operations: list[str]) -> None:
        self._operations = operations
        self.saved_chunks: list[Chunk] = []

    def save_many(self, chunks: list[Chunk]) -> None:
        self._operations.append("chunk_save_many")
        self.saved_chunks.extend(chunks)

    def list_by_document_version(
        self,
        *,
        document_id: str,
        document_version_id: str,
    ) -> list[Chunk]:
        return [
            chunk
            for chunk in self.saved_chunks
            if chunk.document_id == document_id and chunk.document_version_id == document_version_id
        ]

    def delete_by_document_version(
        self,
        *,
        document_id: str,
        document_version_id: str,
    ) -> None:
        self.saved_chunks = [
            chunk
            for chunk in self.saved_chunks
            if not (
                chunk.document_id == document_id
                and chunk.document_version_id == document_version_id
            )
        ]


class SpyChunkGenerator:
    def __init__(self, inner: ChunkGenerator) -> None:
        self._inner = inner
        self.generate_calls: list[str] = []

    def generate(self, normalized_text: str) -> list[ChunkDraft]:
        self.generate_calls.append(normalized_text)
        return self._inner.generate(normalized_text)


class SpyKnowledgeMaterializer:
    def __init__(self, inner: KnowledgeMaterializer) -> None:
        self._inner = inner
        self.materialize_calls: list[tuple[str, str, int]] = []

    def materialize(
        self,
        *,
        document_id: str,
        document_version_id: str,
        chunk_drafts: list[ChunkDraft],
        now: datetime | None = None,
    ) -> KnowledgeMaterializationResult:
        self.materialize_calls.append(
            (document_id, document_version_id, len(chunk_drafts)),
        )
        return self._inner.materialize(
            document_id=document_id,
            document_version_id=document_version_id,
            chunk_drafts=chunk_drafts,
            now=now,
        )


def build_use_case() -> tuple[
    MaterializeKnowledge,
    SpyChunkGenerator,
    SpyKnowledgeMaterializer,
    FakeKnowledgeRepository,
    FakeChunkRepository,
    list[str],
]:
    operations: list[str] = []
    chunk_generator = SpyChunkGenerator(ChunkGenerator(max_chunk_size=MAX_CHUNK_SIZE))
    knowledge_materializer = SpyKnowledgeMaterializer(KnowledgeMaterializer())
    knowledge_repository = FakeKnowledgeRepository(operations)
    chunk_repository = FakeChunkRepository(operations)
    use_case = MaterializeKnowledge(
        chunk_generator=cast(ChunkGenerator, chunk_generator),
        knowledge_materializer=cast(KnowledgeMaterializer, knowledge_materializer),
        knowledge_repository=knowledge_repository,
        chunk_repository=chunk_repository,
    )
    return (
        use_case,
        chunk_generator,
        knowledge_materializer,
        knowledge_repository,
        chunk_repository,
        operations,
    )


def test_materialize_knowledge_orchestrates_domain_services_and_repositories() -> None:
    (
        use_case,
        chunk_generator,
        knowledge_materializer,
        knowledge_repository,
        chunk_repository,
        operations,
    ) = build_use_case()
    normalized_text = "Alpha passage. Beta passage."

    result = use_case.execute(
        MaterializeKnowledgeCommand(
            document_id=DOCUMENT_ID,
            document_version_id=DOCUMENT_VERSION_ID,
            normalized_text=normalized_text,
        )
    )

    assert chunk_generator.generate_calls == [normalized_text]
    assert knowledge_materializer.materialize_calls == [
        (DOCUMENT_ID, DOCUMENT_VERSION_ID, 2),
    ]
    assert operations == ["knowledge_save", "chunk_save_many"]
    assert len(knowledge_repository.saved_items) == 1
    assert len(chunk_repository.saved_chunks) == 2
    assert result.knowledge_item_id == knowledge_repository.saved_items[0].id.value
    assert result.chunk_count == 2


def test_materialize_knowledge_persists_knowledge_item_before_chunks() -> None:
    use_case, _, _, knowledge_repository, chunk_repository, operations = build_use_case()

    use_case.execute(
        MaterializeKnowledgeCommand(
            document_id=DOCUMENT_ID,
            document_version_id=DOCUMENT_VERSION_ID,
            normalized_text="Single chunk text.",
        )
    )

    assert operations.index("knowledge_save") < operations.index("chunk_save_many")
    assert (
        chunk_repository.saved_chunks[0].knowledge_item_id == knowledge_repository.saved_items[0].id
    )


def test_materialize_knowledge_rejects_empty_normalized_text_without_persistence() -> None:
    use_case, chunk_generator, knowledge_materializer, knowledge_repository, chunk_repository, _ = (
        build_use_case()
    )

    with pytest.raises(NoChunksGeneratedError):
        use_case.execute(
            MaterializeKnowledgeCommand(
                document_id=DOCUMENT_ID,
                document_version_id=DOCUMENT_VERSION_ID,
                normalized_text="   ",
            )
        )

    assert chunk_generator.generate_calls == ["   "]
    assert knowledge_materializer.materialize_calls == []
    assert knowledge_repository.saved_items == []
    assert chunk_repository.saved_chunks == []
