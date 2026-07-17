from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session as OrmSession

from memovi_search.domain.entities import Embedding, RankedSearchDocument, SearchDocument
from memovi_search.domain.exceptions import InvalidEmbeddingError
from memovi_search.domain.value_objects import EmbeddingId, EmbeddingVector, SearchDocumentId
from memovi_search.infrastructure.persistence.models import (
    SearchDocumentRecord,
    SearchEmbeddingRecord,
)
from memovi_search.infrastructure.persistence.vector import EMBEDDING_VECTOR_DIMENSIONS


class SqlAlchemyEmbeddingRepository:
    def __init__(self, session: OrmSession) -> None:
        self._session = session

    def save(self, embedding: Embedding) -> None:
        if embedding.dimensions != EMBEDDING_VECTOR_DIMENSIONS:
            raise InvalidEmbeddingError(
                f"Embedding dimensions must be {EMBEDDING_VECTOR_DIMENSIONS} "
                f"for vector storage (got {embedding.dimensions}).",
            )

        record = self._session.get(SearchEmbeddingRecord, embedding.id.value)
        if record is None:
            existing = self._find_by_document_provider_model(
                search_document_id=embedding.search_document_id,
                provider=embedding.provider,
                model=embedding.model,
            )
            if existing is None:
                self._session.add(self._to_record(embedding))
                return
            record = existing

        record.search_document_id = embedding.search_document_id.value
        record.provider = embedding.provider
        record.model = embedding.model
        record.dimensions = embedding.dimensions
        record.vector = list(embedding.vector)

    def get_by_search_document(
        self,
        search_document_id: SearchDocumentId,
    ) -> Embedding | None:
        record = self._session.scalars(
            select(SearchEmbeddingRecord)
            .where(SearchEmbeddingRecord.search_document_id == search_document_id.value)
            .limit(1),
        ).first()
        if record is None:
            return None
        return self._to_domain(record)

    def delete(self, embedding_id: EmbeddingId) -> None:
        record = self._session.get(SearchEmbeddingRecord, embedding_id.value)
        if record is not None:
            self._session.delete(record)

    def similarity_search(
        self,
        query_vector: EmbeddingVector,
        limit: int,
    ) -> list[RankedSearchDocument]:
        if limit <= 0:
            return []
        if query_vector.dimensions != EMBEDDING_VECTOR_DIMENSIONS:
            raise InvalidEmbeddingError(
                f"Query embedding dimensions must be {EMBEDDING_VECTOR_DIMENSIONS} "
                f"(got {query_vector.dimensions}).",
            )
        if not _supports_vector_search(self._session):
            return []

        distance = SearchEmbeddingRecord.vector.cosine_distance(query_vector.values)
        similarity_score = (1 - distance).label("similarity_score")

        rows = self._session.execute(
            select(SearchDocumentRecord, similarity_score)
            .join(
                SearchEmbeddingRecord,
                SearchEmbeddingRecord.search_document_id == SearchDocumentRecord.id,
            )
            .where(SearchEmbeddingRecord.dimensions == query_vector.dimensions)
            .order_by(distance.asc(), SearchDocumentRecord.created_at.asc())
            .limit(limit),
        ).all()

        return [
            RankedSearchDocument(
                search_document=self._document_to_domain(record),
                relevance_score=float(score),
            )
            for record, score in rows
        ]

    def _find_by_document_provider_model(
        self,
        *,
        search_document_id: SearchDocumentId,
        provider: str,
        model: str,
    ) -> SearchEmbeddingRecord | None:
        return self._session.scalars(
            select(SearchEmbeddingRecord).where(
                SearchEmbeddingRecord.search_document_id == search_document_id.value,
                SearchEmbeddingRecord.provider == provider,
                SearchEmbeddingRecord.model == model,
            ),
        ).first()

    def _to_domain(self, record: SearchEmbeddingRecord) -> Embedding:
        return Embedding(
            id=EmbeddingId(record.id),
            search_document_id=SearchDocumentId(record.search_document_id),
            provider=record.provider,
            model=record.model,
            dimensions=record.dimensions,
            vector=tuple(record.vector),
        )

    def _to_record(self, embedding: Embedding) -> SearchEmbeddingRecord:
        return SearchEmbeddingRecord(
            id=embedding.id.value,
            search_document_id=embedding.search_document_id.value,
            provider=embedding.provider,
            model=embedding.model,
            dimensions=embedding.dimensions,
            vector=list(embedding.vector),
        )

    def _document_to_domain(self, record: SearchDocumentRecord) -> SearchDocument:
        return SearchDocument(
            id=SearchDocumentId(record.id),
            knowledge_item_id=record.knowledge_item_id,
            document_id=record.document_id,
            document_version_id=record.document_version_id,
            source_type=record.source_type,
            mime_type=record.mime_type,
            searchable_text=record.searchable_text,
            created_at=_as_utc(record.created_at),
            updated_at=_as_utc(record.updated_at),
        )


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _supports_vector_search(session: OrmSession) -> bool:
    try:
        bind = session.get_bind()
    except Exception:
        return False
    return bind.dialect.name == "postgresql"
