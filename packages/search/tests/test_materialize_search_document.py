import builtins
from typing import cast

import pytest
from memovi_search.application.commands import (
    MaterializeSearchDocument,
    MaterializeSearchDocumentCommand,
)
from memovi_search.domain.entities import Embedding, RankedSearchDocument, SearchDocument
from memovi_search.domain.exceptions import InvalidSearchMaterializationError
from memovi_search.domain.repositories import SearchRepository
from memovi_search.domain.services import SearchMaterializer
from memovi_search.domain.value_objects import EmbeddingId, SearchDocumentId

DOCUMENT_ID = "3b96152e-5ba9-4933-8819-2a08069a6d9f"
DOCUMENT_VERSION_ID = "7ce3e814-de68-4200-973e-b2526eee058d"
KNOWLEDGE_ITEM_ID = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"


class FakeSearchRepository(SearchRepository):
    def __init__(self, operations: list[str]) -> None:
        self._operations = operations
        self.saved_documents: list[SearchDocument] = []

    def save_document(self, search_document: SearchDocument) -> None:
        self._operations.append("document_save")
        self.saved_documents.append(search_document)

    def get_document(self, search_document_id: SearchDocumentId) -> SearchDocument | None:
        for document in self.saved_documents:
            if document.id == search_document_id:
                return document
        return None

    def list_documents(self) -> builtins.list[SearchDocument]:
        return sorted(self.saved_documents, key=lambda document: document.created_at)

    def delete_document(self, search_document_id: SearchDocumentId) -> None:
        self.saved_documents = [
            document for document in self.saved_documents if document.id != search_document_id
        ]

    def search(self, query: str, limit: int, offset: int) -> builtins.list[RankedSearchDocument]:
        return []

    def save_embedding(self, embedding: Embedding) -> None:
        raise NotImplementedError

    def get_embedding(self, embedding_id: EmbeddingId) -> Embedding | None:
        raise NotImplementedError

    def delete_embedding(self, embedding_id: EmbeddingId) -> None:
        raise NotImplementedError


class SpySearchMaterializer:
    def __init__(self, inner: SearchMaterializer) -> None:
        self._inner = inner
        self.materialize_calls: list[tuple[str, str, str, int]] = []

    def materialize(
        self,
        *,
        knowledge_item_id: str,
        document_id: str,
        document_version_id: str,
        chunk_texts: list[str],
        now: object | None = None,
    ) -> SearchDocument:
        self.materialize_calls.append(
            (knowledge_item_id, document_id, document_version_id, len(chunk_texts)),
        )
        return self._inner.materialize(
            knowledge_item_id=knowledge_item_id,
            document_id=document_id,
            document_version_id=document_version_id,
            chunk_texts=chunk_texts,
            now=now,  # type: ignore[arg-type]
        )


def build_use_case() -> tuple[
    MaterializeSearchDocument,
    SpySearchMaterializer,
    FakeSearchRepository,
    list[str],
]:
    operations: list[str] = []
    search_materializer = SpySearchMaterializer(SearchMaterializer())
    search_repository = FakeSearchRepository(operations)
    use_case = MaterializeSearchDocument(
        search_materializer=cast(SearchMaterializer, search_materializer),
        search_repository=search_repository,
    )
    return use_case, search_materializer, search_repository, operations


def test_materialize_search_document_orchestrates_materializer_and_repository() -> None:
    use_case, search_materializer, search_repository, operations = build_use_case()

    result = use_case.execute(
        MaterializeSearchDocumentCommand(
            knowledge_item_id=KNOWLEDGE_ITEM_ID,
            document_id=DOCUMENT_ID,
            document_version_id=DOCUMENT_VERSION_ID,
            chunk_texts=["Alpha passage.", "Beta passage."],
        )
    )

    assert search_materializer.materialize_calls == [
        (KNOWLEDGE_ITEM_ID, DOCUMENT_ID, DOCUMENT_VERSION_ID, 2),
    ]
    assert operations == ["document_save"]
    assert len(search_repository.saved_documents) == 1
    assert result.search_document_id == search_repository.saved_documents[0].id.value
    assert search_repository.saved_documents[0].searchable_text == "Alpha passage.Beta passage."


def test_materialize_search_document_persists_exactly_once() -> None:
    use_case, _, search_repository, operations = build_use_case()

    use_case.execute(
        MaterializeSearchDocumentCommand(
            knowledge_item_id=KNOWLEDGE_ITEM_ID,
            document_id=DOCUMENT_ID,
            document_version_id=DOCUMENT_VERSION_ID,
            chunk_texts=["Single chunk text."],
        )
    )

    assert operations.count("document_save") == 1
    assert len(search_repository.saved_documents) == 1


def test_materialize_search_document_skips_persistence_on_materialization_failure() -> None:
    use_case, search_materializer, search_repository, operations = build_use_case()

    with pytest.raises(InvalidSearchMaterializationError):
        use_case.execute(
            MaterializeSearchDocumentCommand(
                knowledge_item_id=KNOWLEDGE_ITEM_ID,
                document_id=DOCUMENT_ID,
                document_version_id=DOCUMENT_VERSION_ID,
                chunk_texts=["   "],
            )
        )

    assert search_materializer.materialize_calls == [
        (KNOWLEDGE_ITEM_ID, DOCUMENT_ID, DOCUMENT_VERSION_ID, 1),
    ]
    assert operations == []
    assert search_repository.saved_documents == []
