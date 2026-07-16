from sqlalchemy import select
from sqlalchemy.orm import Session as OrmSession

from memovi_search.domain.entities import Embedding
from memovi_search.domain.value_objects import EmbeddingId, SearchDocumentId
from memovi_search.infrastructure.persistence.models import SearchEmbeddingRecord


class SqlAlchemyEmbeddingRepository:
    def __init__(self, session: OrmSession) -> None:
        self._session = session

    def save(self, embedding: Embedding) -> None:
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
