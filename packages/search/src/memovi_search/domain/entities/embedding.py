from dataclasses import dataclass
from datetime import UTC, datetime

from memovi_search.domain.exceptions import InvalidEmbeddingError
from memovi_search.domain.value_objects import EmbeddingId, SearchDocumentId


@dataclass(frozen=True, slots=True)
class Embedding:
    """Metadata describing an embedding produced for a search document."""

    id: EmbeddingId
    search_document_id: SearchDocumentId
    model_id: str
    dimensions: int
    created_at: datetime

    def __post_init__(self) -> None:
        if not self.model_id.strip():
            raise InvalidEmbeddingError("Embedding model ID is required.")
        if self.dimensions <= 0:
            raise InvalidEmbeddingError("Embedding dimensions must be positive.")

    @classmethod
    def record(
        cls,
        *,
        search_document_id: SearchDocumentId,
        model_id: str,
        dimensions: int,
        now: datetime | None = None,
    ) -> Embedding:
        return cls(
            id=EmbeddingId.new(),
            search_document_id=search_document_id,
            model_id=model_id.strip(),
            dimensions=dimensions,
            created_at=now or datetime.now(UTC),
        )
