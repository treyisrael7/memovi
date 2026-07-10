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

    def save_document(self, search_document: SearchDocument) -> None:
        record = self._session.get(SearchDocumentRecord, search_document.id.value)
        if record is None:
            self._session.add(self._document_to_record(search_document))
            return

        record.knowledge_item_id = search_document.knowledge_item_id
        record.document_id = search_document.document_id
        record.document_version_id = search_document.document_version_id
        record.searchable_text = search_document.searchable_text
        record.updated_at = search_document.updated_at

    def get_document(self, search_document_id: SearchDocumentId) -> SearchDocument | None:
        record = self._session.get(SearchDocumentRecord, search_document_id.value)
        if record is None:
            return None
        return self._document_to_domain(record)

    def list_documents(self) -> builtins.list[SearchDocument]:
        records = (
            self._session.query(SearchDocumentRecord)
            .order_by(SearchDocumentRecord.created_at.asc())
            .all()
        )
        return [self._document_to_domain(record) for record in records]

    def delete_document(self, search_document_id: SearchDocumentId) -> None:
        record = self._session.get(SearchDocumentRecord, search_document_id.value)
        if record is not None:
            self._session.delete(record)

    def save_embedding(self, embedding: Embedding) -> None:
        record = self._session.get(SearchEmbeddingRecord, embedding.id.value)
        if record is None:
            self._session.add(self._embedding_to_record(embedding))
            return

        record.search_document_id = embedding.search_document_id.value
        record.provider = embedding.provider
        record.model = embedding.model
        record.dimensions = embedding.dimensions
        record.vector = list(embedding.vector)

    def get_embedding(self, embedding_id: EmbeddingId) -> Embedding | None:
        record = self._session.get(SearchEmbeddingRecord, embedding_id.value)
        if record is None:
            return None
        return self._embedding_to_domain(record)

    def delete_embedding(self, embedding_id: EmbeddingId) -> None:
        record = self._session.get(SearchEmbeddingRecord, embedding_id.value)
        if record is not None:
            self._session.delete(record)

    def _document_to_domain(self, record: SearchDocumentRecord) -> SearchDocument:
        return SearchDocument(
            id=SearchDocumentId(record.id),
            knowledge_item_id=record.knowledge_item_id,
            document_id=record.document_id,
            document_version_id=record.document_version_id,
            searchable_text=record.searchable_text,
            created_at=_as_utc(record.created_at),
            updated_at=_as_utc(record.updated_at),
        )

    def _document_to_record(self, search_document: SearchDocument) -> SearchDocumentRecord:
        return SearchDocumentRecord(
            id=search_document.id.value,
            knowledge_item_id=search_document.knowledge_item_id,
            document_id=search_document.document_id,
            document_version_id=search_document.document_version_id,
            searchable_text=search_document.searchable_text,
            created_at=search_document.created_at,
            updated_at=search_document.updated_at,
        )

    def _embedding_to_domain(self, record: SearchEmbeddingRecord) -> Embedding:
        return Embedding(
            id=EmbeddingId(record.id),
            search_document_id=SearchDocumentId(record.search_document_id),
            provider=record.provider,
            model=record.model,
            dimensions=record.dimensions,
            vector=tuple(record.vector),
        )

    def _embedding_to_record(self, embedding: Embedding) -> SearchEmbeddingRecord:
        return SearchEmbeddingRecord(
            id=embedding.id.value,
            search_document_id=embedding.search_document_id.value,
            provider=embedding.provider,
            model=embedding.model,
            dimensions=embedding.dimensions,
            vector=list(embedding.vector),
        )


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
