from datetime import UTC, datetime

from memovi_search.application.dto import SearchFilters
from memovi_search.application.services import (
    RetrievalEngine,
    RetrievalEngineRequest,
    RetrievalMode,
)
from memovi_search.domain.entities import SearchDocument, SearchResult
from memovi_search.domain.ranking import RankFusion, ScoreNormalizer
from memovi_search.domain.retrievers import RetrievalRequest
from memovi_search.domain.value_objects import SearchDocumentId
from memovi_shared import WorkspaceId

DOCUMENT_ID = "3b96152e-5ba9-4933-8819-2a08069a6d9f"
DOCUMENT_VERSION_ID = "7ce3e814-de68-4200-973e-b2526eee058d"
CREATED = datetime(2026, 7, 13, 12, 0, tzinfo=UTC)


def _document(
    *,
    knowledge_item_id: str,
    text: str,
    mime_type: str = "text/markdown",
    source_type: str = "upload",
    search_document_id: str | None = None,
) -> SearchDocument:
    return SearchDocument(
        id=SearchDocumentId(search_document_id or knowledge_item_id),
        knowledge_item_id=knowledge_item_id,
        document_id=DOCUMENT_ID,
        document_version_id=DOCUMENT_VERSION_ID,
        source_type=source_type,
        mime_type=mime_type,
        searchable_text=text,
        created_at=CREATED,
        updated_at=CREATED,
        workspace_id=WorkspaceId.default(),
    )


class FakeRetriever:

    def __init__(self, results: list[SearchResult]) -> None:
        self.results = results
        self.calls: list[RetrievalRequest] = []

    def retrieve(self, request: RetrievalRequest) -> list[SearchResult]:
        self.calls.append(request)
        return list(self.results)


def test_retrieval_engine_keyword_mode_uses_only_keyword_retriever() -> None:
    document = _document(
        knowledge_item_id="a1b2c3d4-e5f6-7890-abcd-ef1234567890", text="keyword hit"
    )
    keyword = FakeRetriever([SearchResult(search_document=document, score=0.8)])
    semantic = FakeRetriever([])
    engine = RetrievalEngine(
        keyword_retriever=keyword,
        semantic_retriever=semantic,
        rank_fusion=RankFusion(),
        score_normalizer=ScoreNormalizer(),
    )
    results = engine.retrieve(
        RetrievalEngineRequest(
            query="keyword",
            mode=RetrievalMode.KEYWORD,
            limit=10,
            offset=0,
            workspace_id=WorkspaceId.default(),
        )
    )
    assert len(results) == 1
    assert results[0].search_document.knowledge_item_id == document.knowledge_item_id
    assert keyword.calls
    assert not semantic.calls


def test_retrieval_engine_hybrid_fuses_and_deduplicates() -> None:
    shared = _document(knowledge_item_id="a1b2c3d4-e5f6-7890-abcd-ef1234567890", text="shared")
    only_keyword = _document(
        knowledge_item_id="b2c3d4e5-f6a7-8901-bcde-f12345678901", text="keyword only"
    )
    only_semantic = _document(
        knowledge_item_id="c3d4e5f6-a7b8-9012-cdef-123456789012", text="semantic only"
    )
    keyword = FakeRetriever(
        [
            SearchResult(search_document=shared, score=0.9),
            SearchResult(search_document=only_keyword, score=0.5),
        ]
    )
    semantic = FakeRetriever(
        [
            SearchResult(search_document=shared, score=0.95),
            SearchResult(search_document=only_semantic, score=0.4),
        ]
    )
    engine = RetrievalEngine(keyword_retriever=keyword, semantic_retriever=semantic)
    results = engine.retrieve(
        RetrievalEngineRequest(
            query="shared",
            mode=RetrievalMode.HYBRID,
            limit=10,
            offset=0,
            workspace_id=WorkspaceId.default(),
        )
    )
    ids = [item.search_document.knowledge_item_id for item in results]
    assert ids[0] == shared.knowledge_item_id
    assert set(ids) == {
        shared.knowledge_item_id,
        only_keyword.knowledge_item_id,
        only_semantic.knowledge_item_id,
    }
    assert len(ids) == 3


def test_retrieval_engine_applies_metadata_filters_and_pagination() -> None:
    markdown = _document(
        knowledge_item_id="a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        text="markdown",
        mime_type="text/markdown",
    )
    plain = _document(
        knowledge_item_id="b2c3d4e5-f6a7-8901-bcde-f12345678901",
        text="plain",
        mime_type="text/plain",
    )
    keyword = FakeRetriever(
        [
            SearchResult(search_document=markdown, score=0.9),
            SearchResult(search_document=plain, score=0.8),
        ]
    )
    engine = RetrievalEngine(keyword_retriever=keyword, semantic_retriever=FakeRetriever([]))
    results = engine.retrieve(
        RetrievalEngineRequest(
            query="doc",
            mode=RetrievalMode.KEYWORD,
            limit=1,
            offset=0,
            filters=SearchFilters(mime_type="text/plain"),
            workspace_id=WorkspaceId.default(),
        )
    )
    assert len(results) == 1
    assert results[0].search_document.mime_type == "text/plain"
