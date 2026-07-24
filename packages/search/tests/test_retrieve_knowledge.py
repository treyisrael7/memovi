from datetime import UTC, datetime

from memovi_search.application.dto import SearchFilters, SearchResultDto
from memovi_search.application.queries import RetrieveKnowledge, RetrieveKnowledgeQuery
from memovi_search.application.services import RetrievalEngine, RetrievalMode
from memovi_search.domain.entities import SearchDocument, SearchResult
from memovi_search.domain.retrievers import RetrievalRequest
from memovi_shared import WorkspaceId

DOCUMENT_ID = "3b96152e-5ba9-4933-8819-2a08069a6d9f"
DOCUMENT_VERSION_ID = "7ce3e814-de68-4200-973e-b2526eee058d"
KNOWLEDGE_ITEM_ID = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
SOURCE_TYPE = "upload"
MIME_TYPE = "text/markdown"
CREATED = datetime(2026, 7, 13, 12, 0, tzinfo=UTC)


class FakeRetriever:

    def __init__(self, results: list[SearchResult] | None = None) -> None:
        self.results = results or []
        self.calls: list[RetrievalRequest] = []

    def retrieve(self, request: RetrievalRequest) -> list[SearchResult]:
        self.calls.append(request)
        return list(self.results)


def _document(
    *,
    knowledge_item_id: str = KNOWLEDGE_ITEM_ID,
    mime_type: str = MIME_TYPE,
    text: str = "Memovi knowledge platform.",
) -> SearchDocument:
    return SearchDocument(
        id=SearchDocument.create(
            knowledge_item_id=knowledge_item_id,
            document_id=DOCUMENT_ID,
            document_version_id=DOCUMENT_VERSION_ID,
            source_type=SOURCE_TYPE,
            mime_type=mime_type,
            searchable_text=text,
            workspace_id=WorkspaceId.default(),
        ).id,
        knowledge_item_id=knowledge_item_id,
        document_id=DOCUMENT_ID,
        document_version_id=DOCUMENT_VERSION_ID,
        source_type=SOURCE_TYPE,
        mime_type=mime_type,
        searchable_text=text,
        created_at=CREATED,
        updated_at=CREATED,
        workspace_id=WorkspaceId.default(),
    )


def test_retrieve_knowledge_maps_engine_results_to_dtos() -> None:
    document = _document()
    keyword = FakeRetriever([SearchResult(search_document=document, score=0.42)])
    use_case = RetrieveKnowledge(
        retrieval_engine=RetrievalEngine(
            keyword_retriever=keyword, semantic_retriever=FakeRetriever()
        )
    )
    results = use_case.execute(
        RetrieveKnowledgeQuery(
            query="Memovi",
            mode=RetrievalMode.KEYWORD,
            limit=10,
            offset=0,
            workspace_id=WorkspaceId.default(),
        )
    )
    assert results == [
        SearchResultDto(
            search_document_id=document.id.value,
            knowledge_item_id=KNOWLEDGE_ITEM_ID,
            document_id=DOCUMENT_ID,
            relevance_score=1.0,
            searchable_text="Memovi knowledge platform.",
        )
    ]
    assert keyword.calls[0].query == "Memovi"


def test_retrieve_knowledge_applies_filters_and_default_hybrid_mode() -> None:
    markdown = _document(mime_type="text/markdown", text="markdown")
    plain = _document(
        knowledge_item_id="b2c3d4e5-f6a7-8901-bcde-f12345678901",
        mime_type="text/plain",
        text="plain",
    )
    keyword = FakeRetriever(
        [
            SearchResult(search_document=markdown, score=0.9),
            SearchResult(search_document=plain, score=0.8),
        ]
    )
    semantic = FakeRetriever()
    use_case = RetrieveKnowledge(
        retrieval_engine=RetrievalEngine(keyword_retriever=keyword, semantic_retriever=semantic)
    )
    results = use_case.execute(
        RetrieveKnowledgeQuery(
            query="doc",
            limit=10,
            filters=SearchFilters(mime_type="text/plain"),
            workspace_id=WorkspaceId.default(),
        )
    )
    assert len(results) == 1
    assert results[0].searchable_text == "plain"
    assert keyword.calls and semantic.calls


def test_retrieve_knowledge_returns_empty_for_blank_query() -> None:
    keyword = FakeRetriever()
    use_case = RetrieveKnowledge(
        retrieval_engine=RetrievalEngine(
            keyword_retriever=keyword, semantic_retriever=FakeRetriever()
        )
    )
    assert (
        use_case.execute(
            RetrieveKnowledgeQuery(
                query="   ",
                mode=RetrievalMode.KEYWORD,
                limit=10,
                workspace_id=WorkspaceId.default(),
            )
        )
        == []
    )
    assert not keyword.calls
