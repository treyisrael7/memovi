from dataclasses import dataclass
from datetime import UTC, datetime

from memovi_search.application.exceptions import SearchDocumentNotFoundError
from memovi_search.application.ports import EventPublisher
from memovi_search.application.services import EmbeddingGenerationService
from memovi_search.domain.entities import Embedding
from memovi_search.domain.events import EmbeddingGenerated
from memovi_search.domain.repositories import EmbeddingRepository, SearchRepository
from memovi_search.domain.value_objects import SearchDocumentId


@dataclass(frozen=True, slots=True)
class GenerateEmbeddingCommand:
    search_document_id: str


@dataclass(frozen=True, slots=True)
class GenerateEmbeddingResult:
    embedding_id: str
    search_document_id: str
    provider: str
    model: str
    dimensions: int


class GenerateEmbedding:
    """Generates and persists an embedding projection for a search document."""

    def __init__(
        self,
        *,
        search_repository: SearchRepository,
        embedding_repository: EmbeddingRepository,
        embedding_generation_service: EmbeddingGenerationService,
        event_publisher: EventPublisher,
    ) -> None:
        self._search_repository = search_repository
        self._embedding_repository = embedding_repository
        self._embedding_generation_service = embedding_generation_service
        self._event_publisher = event_publisher

    def execute(self, command: GenerateEmbeddingCommand) -> GenerateEmbeddingResult:
        search_document_id = SearchDocumentId(command.search_document_id)
        search_document = self._search_repository.get_document(search_document_id)
        if search_document is None:
            raise SearchDocumentNotFoundError(
                f"Search document '{command.search_document_id}' was not found.",
            )

        vector = self._embedding_generation_service.generate(search_document.searchable_text)
        provider = self._embedding_generation_service.provider
        model = self._embedding_generation_service.model

        existing = self._embedding_repository.get_by_search_document(search_document_id)
        if existing is not None and existing.provider == provider and existing.model == model:
            embedding = Embedding(
                id=existing.id,
                search_document_id=search_document_id,
                provider=provider,
                model=model,
                dimensions=vector.dimensions,
                vector=tuple(vector.values),
            )
        else:
            if existing is not None:
                self._embedding_repository.delete(existing.id)
            embedding = Embedding.create(
                search_document_id=search_document_id,
                provider=provider,
                model=model,
                vector=list(vector.values),
            )

        self._embedding_repository.save(embedding)

        result = GenerateEmbeddingResult(
            embedding_id=embedding.id.value,
            search_document_id=search_document_id.value,
            provider=embedding.provider,
            model=embedding.model,
            dimensions=embedding.dimensions,
        )
        self._event_publisher.publish(
            EmbeddingGenerated(
                embedding_id=result.embedding_id,
                search_document_id=result.search_document_id,
                provider=result.provider,
                model=result.model,
                dimensions=result.dimensions,
                generated_at=datetime.now(UTC),
            ),
        )
        return result
