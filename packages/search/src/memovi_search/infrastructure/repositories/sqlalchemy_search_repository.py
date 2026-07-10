import builtins
from datetime import UTC, datetime

from sqlalchemy.orm import Session as OrmSession

from memovi_search.domain.entities import Embedding, SearchDocument
from memovi_search.domain.value_objects import EmbeddingId, SearchDocumentId
from memovi_search.infrastructure.persistence.models import (
    SearchDocumentRecord,
    SearchEmbeddingRecord,
)


class SqlAlchemySearchRepository:
    def __init__(self, session: OrmSession) -> None:
        self._session = session

    def save_search_document(self, search_document: SearchDocument) -> None:
        record = self._session.get(SearchDocumentRecord, search_document.id.value)
        if record is None:
            self._session.add(self._search_document_to_record(search_document))
            return

        record.document_id = search_document.document_id
        record.document_version_id = search_document.document_version_id
        record.chunk_id = search_document.chunk_id
        record.updated_at = search_document.updated_at

    def get_search_document(
        self,
        search_document_id: SearchDocumentId,
    ) -> SearchDocument | None:
        record = self._session.get(SearchDocumentRecord, search_document_id.value)
        if record is None:
            return None
        return self._search_document_to_domain(record)

    def list_search_documents_by_document(
        self,
        *,
        document_id: str,
    ) -> builtins.list[SearchDocument]:
        records = (
            self._session.query(SearchDocumentRecord)
            .filter(SearchDocumentRecord.document_id == document_id)
            .order_by(SearchDocumentRecord.created_at.asc())
            .all()
        )
        return [self._search_document_to_domain(record) for record in records]

    def list_search_documents_by_chunk(
        self,
        *,
        chunk_id: str,
    ) -> builtins.list[SearchDocument]:
        records = (
            self._session.query(SearchDocumentRecord)
            .filter(SearchDocumentRecord.chunk_id == chunk_id)
            .order_by(SearchDocumentRecord.created_at.asc())
            .all()
        )
        return [self._search_document_to_domain(record) for record in records]

    def delete_search_document(self, search_document_id: SearchDocumentId) -> None:
        record = self._session.get(SearchDocumentRecord, search_document_id.value)
        if record is not None:
            self._session.delete(record)

    def save_embedding(self, embedding: Embedding) -> None:
        record = self._session.get(SearchEmbeddingRecord, embedding.id.value)
        if record is None:
            self._session.add(self._embedding_to_record(embedding))
            return

        record.search_document_id = embedding.search_document_id.value
        record.model_id = embedding.model_id
        record.dimensions = embedding.dimensions

    def get_embedding(self, embedding_id: EmbeddingId) -> Embedding | None:
        record = self._session.get(SearchEmbeddingRecord, embedding_id.value)
        if record is None:
            return None
        return self._embedding_to_domain(record)

    def list_embeddings_for_search_document(
        self,
        *,
        search_document_id: SearchDocumentId,
    ) -> builtins.list[Embedding]:
        records = (
            self._session.query(SearchEmbeddingRecord)
            .filter(SearchEmbeddingRecord.search_document_id == search_document_id.value)
            .order_by(SearchEmbeddingRecord.created_at.asc())
            .all()
        )
        return [self._embedding_to_domain(record) for record in records]

    def delete_embedding(self, embedding_id: EmbeddingId) -> None:
        record = self._session.get(SearchEmbeddingRecord, embedding_id.value)
        if record is not None:
            self._session.delete(record)

    def _search_document_to_domain(self, record: SearchDocumentRecord) -> SearchDocument:
        return SearchDocument(
            id=SearchDocumentId(record.id),
            document_id=record.document_id,
            document_version_id=record.document_version_id,
            chunk_id=record.chunk_id,
            created_at=_as_utc(record.created_at),
            updated_at=_as_utc(record.updated_at),
        )

    def _search_document_to_record(self, search_document: SearchDocument) -> SearchDocumentRecord:
        return SearchDocumentRecord(
            id=search_document.id.value,
            document_id=search_document.document_id,
            document_version_id=search_document.document_version_id,
            chunk_id=search_document.chunk_id,
            created_at=search_document.created_at,
            updated_at=search_document.updated_at,
        )

    def _embedding_to_domain(self, record: SearchEmbeddingRecord) -> Embedding:
        return Embedding(
            id=EmbeddingId(record.id),
            search_document_id=SearchDocumentId(record.search_document_id),
            model_id=record.model_id,
            dimensions=record.dimensions,
            created_at=_as_utc(record.created_at),
        )

    def _embedding_to_record(self, embedding: Embedding) -> SearchEmbeddingRecord:
        return SearchEmbeddingRecord(
            id=embedding.id.value,
            search_document_id=embedding.search_document_id.value,
            model_id=embedding.model_id,
            dimensions=embedding.dimensions,
            created_at=embedding.created_at,
        )


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
