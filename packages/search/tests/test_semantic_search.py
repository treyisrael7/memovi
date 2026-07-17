from memovi_search.application.dto import SearchResultDto
from memovi_search.application.queries import SemanticSearch, SemanticSearchQuery
from memovi_search.application.services import RetrievalEngine
from memovi_search.domain.entities import SearchDocument, SearchResult
from memovi_search.domain.retrievers import RetrievalRequest
from memovi_search.infrastructure.providers import FakeEmbeddingProvider

DOCUMENT_ID = "3b96152e-5ba9-4933-8819-2a08069a6d9f"
DOCUMENT_VERSION_ID = "7ce3e814-de68-4200-973e-b2526eee058d"
KNOWLEDGE_ITEM_ID = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
SOURCE_TYPE = "upload"
MIME_TYPE = "text/markdown"


class FakeRetriever:
    def __init__(self, results: list[SearchResult] | None = None) -> None:
        self.results = results or []
        self.calls: list[RetrievalRequest] = []

    def retrieve(self, request: RetrievalRequest) -> list[SearchResult]:
        self.calls.append(request)
        return list(self.results)


def test_semantic_search_facade_uses_semantic_mode() -> None:
    search_document = SearchDocument.create(
        knowledge_item_id=KNOWLEDGE_ITEM_ID,
        document_id=DOCUMENT_ID,
        document_version_id=DOCUMENT_VERSION_ID,
        source_type=SOURCE_TYPE,
        mime_type=MIME_TYPE,
        searchable_text="Memovi knowledge platform.",
    )
    semantic = FakeRetriever(
        [SearchResult(search_document=search_document, score=0.91)],
    )
    keyword = FakeRetriever()
    use_case = SemanticSearch(
        retrieval_engine=RetrievalEngine(
            keyword_retriever=keyword,
            semantic_retriever=semantic,
        ),
    )

    results = use_case.execute(SemanticSearchQuery(query="  Memovi  ", limit=10))

    assert results == [
        SearchResultDto(
            search_document_id=search_document.id.value,
            knowledge_item_id=KNOWLEDGE_ITEM_ID,
            document_id=DOCUMENT_ID,
            relevance_score=1.0,
            searchable_text="Memovi knowledge platform.",
        )
    ]
    assert semantic.calls
    assert not keyword.calls
    assert FakeEmbeddingProvider().embed("Memovi").dimensions == 4


def test_semantic_search_returns_empty_for_blank_query() -> None:
    semantic = FakeRetriever()
    use_case = SemanticSearch(
        retrieval_engine=RetrievalEngine(
            keyword_retriever=FakeRetriever(),
            semantic_retriever=semantic,
        ),
    )

    assert use_case.execute(SemanticSearchQuery(query="   ", limit=10)) == []
    assert not semantic.calls
