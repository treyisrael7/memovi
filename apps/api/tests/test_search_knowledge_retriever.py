import pytest
from api.intelligence_integration import SearchKnowledgeRetriever
from memovi_intelligence.application.services import ContextAssembler, PromptBuilder
from memovi_intelligence.config import IntelligenceConfig
from memovi_intelligence.domain.entities import ReasoningRequest
from memovi_intelligence.domain.value_objects import Citation
from memovi_search.application.dto import SearchResultDto
from memovi_search.application.queries import RetrieveKnowledgeQuery
from memovi_search.application.services import RetrievalMode
from memovi_shared import WorkspaceId


class FakeRetrieveKnowledge:

    def __init__(
        self, results: list[SearchResultDto] | None = None, *, error: Exception | None = None
    ) -> None:
        self._results = results if results is not None else []
        self._error = error
        self.last_query: RetrieveKnowledgeQuery | None = None
        self.call_count = 0

    def execute(self, query: RetrieveKnowledgeQuery) -> list[SearchResultDto]:
        self.call_count += 1
        self.last_query = query
        if self._error is not None:
            raise self._error
        return list(self._results)


def _result(
    *,
    search_document_id: str = "sd-1",
    knowledge_item_id: str = "ki-1",
    document_id: str = "doc-1",
    relevance_score: float = 0.87,
    searchable_text: str = "Indexed chunk about quantum memory.",
) -> SearchResultDto:
    return SearchResultDto(
        search_document_id=search_document_id,
        knowledge_item_id=knowledge_item_id,
        document_id=document_id,
        relevance_score=relevance_score,
        searchable_text=searchable_text,
    )


def _request(query: str = "What is quantum memory?") -> ReasoningRequest:
    return ReasoningRequest.create(query=query)


def test_successful_retrieval() -> None:
    fake = FakeRetrieveKnowledge(results=[_result()])
    retriever = SearchKnowledgeRetriever(
        retrieve_knowledge=fake,
        workspace_id=WorkspaceId.default(),
    )
    items = retriever.retrieve(_request(), limit=5)
    assert len(items) == 1
    assert items[0].chunk_id == "sd-1"
    assert items[0].document_id == "doc-1"
    assert items[0].text == "Indexed chunk about quantum memory."
    assert items[0].score == 0.87
    assert fake.last_query == RetrieveKnowledgeQuery(
        query="What is quantum memory?",
        limit=5,
        mode=RetrievalMode.HYBRID,
        workspace_id=WorkspaceId.default(),
    )


def test_empty_retrieval() -> None:
    fake = FakeRetrieveKnowledge(results=[])
    retriever = SearchKnowledgeRetriever(
        retrieve_knowledge=fake,
        workspace_id=WorkspaceId.default(),
    )
    items = retriever.retrieve(_request(), limit=10)
    assert items == ()
    assert fake.call_count == 1


def test_metadata_mapping() -> None:
    """Identity metadata from SearchResultDto maps into RetrievedKnowledge fields."""
    search_result = _result(
        search_document_id="search-doc-42",
        knowledge_item_id="knowledge-99",
        document_id="document-7",
        searchable_text="Canonical searchable body.",
    )
    fake = FakeRetrieveKnowledge(results=[search_result])
    retriever = SearchKnowledgeRetriever(
        retrieve_knowledge=fake,
        workspace_id=WorkspaceId.default(),
    )
    item = retriever.retrieve(_request(), limit=1)[0]
    assert item.chunk_id == search_result.search_document_id
    assert item.document_id == search_result.document_id
    assert item.text == search_result.searchable_text
    assert item.document_title is None
    assert search_result.knowledge_item_id == "knowledge-99"


def test_citation_mapping() -> None:
    """Mapped fields are sufficient for PromptBuilder citation construction."""
    fake = FakeRetrieveKnowledge(
        results=[
            _result(
                search_document_id="chunk-cite",
                document_id="doc-cite",
                relevance_score=0.91,
                searchable_text="Citation-bearing knowledge text.",
            )
        ]
    )
    retriever = SearchKnowledgeRetriever(
        retrieve_knowledge=fake,
        workspace_id=WorkspaceId.default(),
    )
    request = _request("Cite this knowledge")
    items = retriever.retrieve(request, limit=3)
    context = ContextAssembler(
        knowledge_retriever=retriever, config=IntelligenceConfig(provider="fake")
    ).assemble_from(request, items)
    prompt = PromptBuilder().build(context)
    assert prompt.citations == (
        Citation(document_id="doc-cite", chunk_id="chunk-cite", document_title=None, score=0.91),
    )
    assert "Citation-bearing knowledge text." in prompt.section("retrieved_knowledge").content
    assert "chunk-cite" in prompt.section("citations").content


def test_score_mapping() -> None:
    fake = FakeRetrieveKnowledge(results=[_result(relevance_score=0.42)])
    retriever = SearchKnowledgeRetriever(
        retrieve_knowledge=fake,
        workspace_id=WorkspaceId.default(),
    )
    item = retriever.retrieve(_request(), limit=1)[0]
    assert item.score == 0.42


def test_multiple_search_results() -> None:
    fake = FakeRetrieveKnowledge(
        results=[
            _result(
                search_document_id="sd-a",
                document_id="doc-a",
                relevance_score=0.9,
                searchable_text="First indexed chunk.",
            ),
            _result(
                search_document_id="sd-b",
                document_id="doc-b",
                relevance_score=0.8,
                searchable_text="Second indexed chunk.",
            ),
            _result(
                search_document_id="sd-c",
                document_id="doc-a",
                relevance_score=0.7,
                searchable_text="Third indexed chunk.",
            ),
        ]
    )
    retriever = SearchKnowledgeRetriever(
        retrieve_knowledge=fake,
        workspace_id=WorkspaceId.default(),
    )
    items = retriever.retrieve(_request(), limit=10)
    assert len(items) == 3
    assert [item.chunk_id for item in items] == ["sd-a", "sd-b", "sd-c"]
    assert [item.score for item in items] == [0.9, 0.8, 0.7]
    assert items[0].text == "First indexed chunk."
    assert items[2].document_id == "doc-a"


def test_retrieval_errors_propagate() -> None:
    fake = FakeRetrieveKnowledge(error=RuntimeError("retrieval failed"))
    retriever = SearchKnowledgeRetriever(
        retrieve_knowledge=fake,
        workspace_id=WorkspaceId.default(),
    )
    with pytest.raises(RuntimeError, match="retrieval failed"):
        retriever.retrieve(_request(), limit=5)
