from memovi_search.domain.entities import RankedSearchDocument, SearchDocument, SearchResult
from memovi_search.domain.retrievers import RetrievalRequest, SemanticRetriever
from memovi_search.domain.value_objects import EmbeddingVector
from memovi_search.infrastructure.providers import FakeEmbeddingProvider
from memovi_shared import WorkspaceId

DOCUMENT_ID = "3b96152e-5ba9-4933-8819-2a08069a6d9f"
DOCUMENT_VERSION_ID = "7ce3e814-de68-4200-973e-b2526eee058d"
KNOWLEDGE_ITEM_ID = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"


class FakeEmbeddingRepository:

    def __init__(self) -> None:
        self.last_similarity_search: tuple[EmbeddingVector, int] | None = None
        self.results: list[RankedSearchDocument] = []

    def save(self, embedding: object) -> None:
        raise NotImplementedError

    def get_by_search_document(self, search_document_id: object) -> None:
        raise NotImplementedError

    def delete(self, embedding_id: object) -> None:
        raise NotImplementedError

    def similarity_search(
        self,
        query_vector: EmbeddingVector,
        limit: int,
        *,
        workspace_id: WorkspaceId | None = None,
    ) -> list[RankedSearchDocument]:
        self.last_similarity_search = (query_vector, limit)
        return self.results[:limit]


def test_semantic_retriever_embeds_query_and_maps_hits() -> None:
    document = SearchDocument.create(
        knowledge_item_id=KNOWLEDGE_ITEM_ID,
        document_id=DOCUMENT_ID,
        document_version_id=DOCUMENT_VERSION_ID,
        source_type="upload",
        mime_type="text/markdown",
        searchable_text="Memovi knowledge",
        workspace_id=WorkspaceId.default(),
    )
    repository = FakeEmbeddingRepository()
    repository.results = [RankedSearchDocument(search_document=document, relevance_score=0.91)]
    provider = FakeEmbeddingProvider()
    retriever = SemanticRetriever(embedding_provider=provider, embedding_repository=repository)
    results = retriever.retrieve(
        RetrievalRequest(query="  Memovi  ", limit=5, workspace_id=WorkspaceId.default())
    )
    assert results == [SearchResult(search_document=document, score=0.91)]
    assert repository.last_similarity_search is not None
    query_vector, limit = repository.last_similarity_search
    assert limit == 5
    assert query_vector == provider.embed("Memovi")


def test_semantic_retriever_returns_empty_for_blank_query() -> None:
    repository = FakeEmbeddingRepository()
    retriever = SemanticRetriever(
        embedding_provider=FakeEmbeddingProvider(), embedding_repository=repository
    )
    assert (
        retriever.retrieve(RetrievalRequest(query=" ", limit=5, workspace_id=WorkspaceId.default()))
        == []
    )
    assert repository.last_similarity_search is None
