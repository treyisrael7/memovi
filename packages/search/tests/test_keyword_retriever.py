from memovi_shared import WorkspaceId
from memovi_search.domain.entities import SearchDocument, SearchResult
from memovi_search.domain.retrievers import KeywordRetriever, RetrievalRequest
DOCUMENT_ID = '3b96152e-5ba9-4933-8819-2a08069a6d9f'
DOCUMENT_VERSION_ID = '7ce3e814-de68-4200-973e-b2526eee058d'
KNOWLEDGE_ITEM_ID = 'a1b2c3d4-e5f6-7890-abcd-ef1234567890'

class FakeSearchRepository:

    def __init__(self) -> None:
        self.last_search: tuple[object, ...] | None = None
        self.results: list = []

    def save_document(self, search_document: object) -> None:
        raise NotImplementedError

    def get_document(self, search_document_id: object) -> None:
        raise NotImplementedError

    def list_documents(self) -> list:
        return []

    def delete_document(self, search_document_id: object) -> None:
        raise NotImplementedError

    def search(self, query: str, limit: int, offset: int, **kwargs: object) -> list:
        self.last_search = (query, limit, offset, kwargs)
        return self.results[:limit]

def _document(text: str='Memovi knowledge') -> SearchDocument:
    return SearchDocument.create(knowledge_item_id=KNOWLEDGE_ITEM_ID, document_id=DOCUMENT_ID, document_version_id=DOCUMENT_VERSION_ID, source_type='upload', mime_type='text/markdown', searchable_text=text, workspace_id=WorkspaceId.default())

def test_keyword_retriever_maps_repository_hits() -> None:
    from memovi_search.domain.entities import RankedSearchDocument
    document = _document()
    repository = FakeSearchRepository()
    repository.results = [RankedSearchDocument(search_document=document, relevance_score=0.42)]
    retriever = KeywordRetriever(search_repository=repository)
    results = retriever.retrieve(RetrievalRequest(query='  Memovi  ', limit=10, workspace_id=WorkspaceId.default()))
    assert results == [SearchResult(search_document=document, score=0.42)]
    assert repository.last_search == (
        "Memovi",
        10,
        0,
        {"workspace_id": WorkspaceId.default()},
    )

def test_keyword_retriever_returns_empty_for_blank_query() -> None:
    repository = FakeSearchRepository()
    retriever = KeywordRetriever(search_repository=repository)
    assert retriever.retrieve(RetrievalRequest(query='   ', limit=10, workspace_id=WorkspaceId.default())) == []
    assert repository.last_search is None
