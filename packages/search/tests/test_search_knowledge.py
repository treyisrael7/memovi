import builtins

from memovi_search.application.queries import SearchKnowledge, SearchKnowledgeQuery
from memovi_search.domain.entities import Embedding, RankedSearchDocument, SearchDocument
from memovi_search.domain.repositories import SearchRepository
from memovi_search.domain.value_objects import EmbeddingId, SearchDocumentId

DOCUMENT_ID = "3b96152e-5ba9-4933-8819-2a08069a6d9f"
DOCUMENT_VERSION_ID = "7ce3e814-de68-4200-973e-b2526eee058d"
KNOWLEDGE_ITEM_ID = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"


class FakeSearchRepository(SearchRepository):
    def __init__(self, search_results: builtins.list[RankedSearchDocument] | None = None) -> None:
        self._search_results = search_results or []

    def save_document(self, search_document: SearchDocument) -> None:
        raise NotImplementedError

    def get_document(self, search_document_id: SearchDocumentId) -> SearchDocument | None:
        raise NotImplementedError

    def list_documents(self) -> builtins.list[SearchDocument]:
        raise NotImplementedError

    def delete_document(self, search_document_id: SearchDocumentId) -> None:
        raise NotImplementedError

    def search(self, query: str, limit: int, offset: int) -> builtins.list[RankedSearchDocument]:
        self.last_search = (query, limit, offset)
        return self._search_results

    def save_embedding(self, embedding: Embedding) -> None:
        raise NotImplementedError

    def get_embedding(self, embedding_id: EmbeddingId) -> Embedding | None:
        raise NotImplementedError

    def delete_embedding(self, embedding_id: EmbeddingId) -> None:
        raise NotImplementedError


def test_search_knowledge_maps_ranked_documents_to_result_dtos() -> None:
    search_document = SearchDocument.create(
        knowledge_item_id=KNOWLEDGE_ITEM_ID,
        document_id=DOCUMENT_ID,
        document_version_id=DOCUMENT_VERSION_ID,
        searchable_text="Memovi knowledge platform.",
    )
    repository = FakeSearchRepository(
        search_results=[
            RankedSearchDocument(
                search_document=search_document,
                relevance_score=0.42,
            )
        ],
    )
    use_case = SearchKnowledge(search_repository=repository)

    results = use_case.execute(
        SearchKnowledgeQuery(
            query="Memovi",
            limit=10,
            offset=0,
        )
    )

    assert repository.last_search == ("Memovi", 10, 0)
    assert len(results) == 1
    assert results[0].search_document_id == search_document.id.value
    assert results[0].knowledge_item_id == KNOWLEDGE_ITEM_ID
    assert results[0].document_id == DOCUMENT_ID
    assert results[0].relevance_score == 0.42
    assert results[0].searchable_text == "Memovi knowledge platform."


def test_search_knowledge_returns_empty_results_for_blank_query() -> None:
    repository = FakeSearchRepository()
    use_case = SearchKnowledge(search_repository=repository)

    results = use_case.execute(
        SearchKnowledgeQuery(
            query="   ",
            limit=10,
            offset=0,
        )
    )

    assert results == []
    assert not hasattr(repository, "last_search")
