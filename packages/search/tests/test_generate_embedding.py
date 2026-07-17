from datetime import UTC, datetime

import pytest
from memovi_search.application.commands import GenerateEmbedding, GenerateEmbeddingCommand
from memovi_search.application.exceptions import SearchDocumentNotFoundError
from memovi_search.application.services import EmbeddingGenerationService
from memovi_search.domain.entities import Embedding, RankedSearchDocument, SearchDocument
from memovi_search.domain.events import EmbeddingGenerated
from memovi_search.domain.repositories import EmbeddingRepository, SearchRepository
from memovi_search.domain.value_objects import EmbeddingId, EmbeddingVector, SearchDocumentId
from memovi_search.infrastructure.providers import FakeEmbeddingProvider

DOCUMENT_ID = "3b96152e-5ba9-4933-8819-2a08069a6d9f"
DOCUMENT_VERSION_ID = "7ce3e814-de68-4200-973e-b2526eee058d"
KNOWLEDGE_ITEM_ID = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
SOURCE_TYPE = "upload"
MIME_TYPE = "text/markdown"
SEARCHABLE_TEXT = "Alpha passage. Beta passage."


class FakeSearchRepository(SearchRepository):
    def __init__(self, documents: list[SearchDocument] | None = None) -> None:
        self.documents = {document.id.value: document for document in (documents or [])}

    def save_document(self, search_document: SearchDocument) -> None:
        self.documents[search_document.id.value] = search_document

    def get_document(self, search_document_id: SearchDocumentId) -> SearchDocument | None:
        return self.documents.get(search_document_id.value)

    def list_documents(self) -> list[SearchDocument]:
        return list(self.documents.values())

    def delete_document(self, search_document_id: SearchDocumentId) -> None:
        self.documents.pop(search_document_id.value, None)

    def search(
        self,
        query: str,
        limit: int,
        offset: int,
        *,
        document_id: str | None = None,
        document_version_id: str | None = None,
        source_type: str | None = None,
        mime_type: str | None = None,
        created_after: datetime | None = None,
        created_before: datetime | None = None,
    ) -> list[RankedSearchDocument]:
        return []


class FakeEmbeddingRepository(EmbeddingRepository):
    def __init__(self) -> None:
        self.embeddings: dict[str, Embedding] = {}
        self.saved: list[Embedding] = []
        self.deleted_ids: list[str] = []

    def save(self, embedding: Embedding) -> None:
        self.embeddings[embedding.id.value] = embedding
        self.saved.append(embedding)

    def get_by_search_document(
        self,
        search_document_id: SearchDocumentId,
    ) -> Embedding | None:
        for embedding in self.embeddings.values():
            if embedding.search_document_id == search_document_id:
                return embedding
        return None

    def delete(self, embedding_id: EmbeddingId) -> None:
        self.deleted_ids.append(embedding_id.value)
        self.embeddings.pop(embedding_id.value, None)

    def similarity_search(
        self,
        query_vector: EmbeddingVector,
        limit: int,
    ) -> list[RankedSearchDocument]:
        return []


class FakeEventPublisher:
    def __init__(self) -> None:
        self.published_events: list[object] = []

    def publish(self, event: object) -> None:
        self.published_events.append(event)


def _search_document() -> SearchDocument:
    return SearchDocument(
        id=SearchDocumentId.new(),
        knowledge_item_id=KNOWLEDGE_ITEM_ID,
        document_id=DOCUMENT_ID,
        document_version_id=DOCUMENT_VERSION_ID,
        source_type=SOURCE_TYPE,
        mime_type=MIME_TYPE,
        searchable_text=SEARCHABLE_TEXT,
        created_at=datetime(2026, 7, 10, 12, 0, tzinfo=UTC),
        updated_at=datetime(2026, 7, 10, 12, 0, tzinfo=UTC),
    )


def _build_use_case(
    *,
    documents: list[SearchDocument] | None = None,
) -> tuple[
    GenerateEmbedding,
    FakeSearchRepository,
    FakeEmbeddingRepository,
    FakeEmbeddingProvider,
    FakeEventPublisher,
]:
    provider = FakeEmbeddingProvider()
    search_repository = FakeSearchRepository(documents)
    embedding_repository = FakeEmbeddingRepository()
    event_publisher = FakeEventPublisher()
    use_case = GenerateEmbedding(
        search_repository=search_repository,
        embedding_repository=embedding_repository,
        embedding_generation_service=EmbeddingGenerationService(provider=provider),
        event_publisher=event_publisher,
    )
    return use_case, search_repository, embedding_repository, provider, event_publisher


def test_generate_embedding_loads_document_generates_persists_and_publishes() -> None:
    search_document = _search_document()
    use_case, _, embedding_repository, provider, event_publisher = _build_use_case(
        documents=[search_document],
    )

    result = use_case.execute(
        GenerateEmbeddingCommand(search_document_id=search_document.id.value),
    )

    assert len(embedding_repository.saved) == 1
    embedding = embedding_repository.saved[0]
    assert result.embedding_id == embedding.id.value
    assert result.search_document_id == search_document.id.value
    assert result.provider == provider.provider
    assert result.model == provider.model
    assert result.dimensions == embedding.dimensions
    assert embedding.vector == tuple(provider.embed(SEARCHABLE_TEXT).values)
    assert len(event_publisher.published_events) == 1
    published = event_publisher.published_events[0]
    assert isinstance(published, EmbeddingGenerated)
    assert published.embedding_id == embedding.id.value
    assert published.search_document_id == search_document.id.value
    assert published.provider == provider.provider
    assert published.model == provider.model
    assert published.dimensions == embedding.dimensions


def test_generate_embedding_updates_existing_projection_for_same_provider_model() -> None:
    search_document = _search_document()
    use_case, _, embedding_repository, provider, _event_publisher = _build_use_case(
        documents=[search_document],
    )
    existing = Embedding.create(
        search_document_id=search_document.id,
        provider=provider.provider,
        model=provider.model,
        vector=[0.0, 0.0, 0.0, 0.0],
    )
    embedding_repository.save(existing)

    result = use_case.execute(
        GenerateEmbeddingCommand(search_document_id=search_document.id.value),
    )

    assert result.embedding_id == existing.id.value
    assert embedding_repository.deleted_ids == []
    assert len(embedding_repository.embeddings) == 1
    assert embedding_repository.embeddings[existing.id.value].vector != (0.0, 0.0, 0.0, 0.0)


def test_generate_embedding_replaces_projection_when_provider_changes() -> None:
    search_document = _search_document()
    use_case, _, embedding_repository, provider, _event_publisher = _build_use_case(
        documents=[search_document],
    )
    existing = Embedding.create(
        search_document_id=search_document.id,
        provider="openai",
        model="text-embedding-3-small",
        vector=[0.1, 0.2],
    )
    embedding_repository.save(existing)

    result = use_case.execute(
        GenerateEmbeddingCommand(search_document_id=search_document.id.value),
    )

    assert existing.id.value in embedding_repository.deleted_ids
    assert result.embedding_id != existing.id.value
    assert result.provider == provider.provider
    assert embedding_repository.get_by_search_document(search_document.id) is not None


def test_generate_embedding_raises_when_search_document_missing() -> None:
    use_case, _, embedding_repository, _provider, event_publisher = _build_use_case()

    with pytest.raises(SearchDocumentNotFoundError):
        use_case.execute(
            GenerateEmbeddingCommand(search_document_id=str(SearchDocumentId.new())),
        )

    assert embedding_repository.saved == []
    assert event_publisher.published_events == []


def test_fake_provider_returns_embedding_vector() -> None:
    provider = FakeEmbeddingProvider()

    vector = provider.embed("text")

    assert isinstance(vector, EmbeddingVector)
    assert vector.dimensions == 4
