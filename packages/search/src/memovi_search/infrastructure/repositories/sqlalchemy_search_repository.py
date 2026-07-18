import builtins
from datetime import UTC, datetime

from memovi_observability import timed_operation
from memovi_shared import WorkspaceId
from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session as OrmSession

from memovi_search.domain.entities import RankedSearchDocument, SearchDocument
from memovi_search.domain.value_objects import SearchDocumentId
from memovi_search.infrastructure.persistence.full_text import ENGLISH_TEXT_SEARCH_CONFIG
from memovi_search.infrastructure.persistence.models import SearchDocumentRecord

_REPO = "SqlAlchemySearchRepository"


class SqlAlchemySearchRepository:
    def __init__(self, session: OrmSession) -> None:
        self._session = session

    def save_document(self, search_document: SearchDocument) -> None:
        with timed_operation("repository.save_document", repository=_REPO):
            record = self._session.get(SearchDocumentRecord, search_document.id.value)
            if record is None:
                record = self._document_to_record(search_document)
                self._session.add(record)
            else:
                record.workspace_id = search_document.workspace_id.value
                record.knowledge_item_id = search_document.knowledge_item_id
                record.document_id = search_document.document_id
                record.document_version_id = search_document.document_version_id
                record.source_type = search_document.source_type
                record.mime_type = search_document.mime_type
                record.searchable_text = search_document.searchable_text
                record.updated_at = search_document.updated_at

            record.search_vector = _search_vector_expression(
                self._session,
                search_document.searchable_text,
            )

    def get_document(
        self,
        search_document_id: SearchDocumentId,
        *,
        workspace_id: WorkspaceId | None = None,
    ) -> SearchDocument | None:
        query = self._session.query(SearchDocumentRecord).filter(
            SearchDocumentRecord.id == search_document_id.value,
        )
        if workspace_id is not None:
            query = query.filter(SearchDocumentRecord.workspace_id == workspace_id.value)
        record = query.one_or_none()
        if record is None:
            return None
        return self._document_to_domain(record)

    def list_documents(self, *, workspace_id: WorkspaceId) -> builtins.list[SearchDocument]:
        records = (
            self._session.query(SearchDocumentRecord)
            .filter(SearchDocumentRecord.workspace_id == workspace_id.value)
            .order_by(SearchDocumentRecord.created_at.asc())
            .all()
        )
        return [self._document_to_domain(record) for record in records]

    def delete_document(
        self,
        search_document_id: SearchDocumentId,
        *,
        workspace_id: WorkspaceId | None = None,
    ) -> None:
        query = self._session.query(SearchDocumentRecord).filter(
            SearchDocumentRecord.id == search_document_id.value,
        )
        if workspace_id is not None:
            query = query.filter(SearchDocumentRecord.workspace_id == workspace_id.value)
        record = query.one_or_none()
        if record is not None:
            self._session.delete(record)

    def search(
        self,
        query: str,
        limit: int,
        offset: int,
        *,
        workspace_id: WorkspaceId,
        document_id: str | None = None,
        document_version_id: str | None = None,
        source_type: str | None = None,
        mime_type: str | None = None,
        created_after: datetime | None = None,
        created_before: datetime | None = None,
    ) -> builtins.list[RankedSearchDocument]:
        with timed_operation("repository.search", repository=_REPO):
            if not _supports_full_text_search(self._session):
                return []

            ts_query = func.plainto_tsquery(ENGLISH_TEXT_SEARCH_CONFIG, query)
            relevance_score = func.ts_rank(
                SearchDocumentRecord.search_vector,
                ts_query,
            ).label("relevance_score")

            statement: Select[tuple[SearchDocumentRecord, float]] = select(
                SearchDocumentRecord,
                relevance_score,
            ).where(
                SearchDocumentRecord.search_vector.op("@@")(ts_query),
                SearchDocumentRecord.workspace_id == workspace_id.value,
            )
            statement = _apply_search_filters(
                statement,
                document_id=document_id,
                document_version_id=document_version_id,
                source_type=source_type,
                mime_type=mime_type,
                created_after=created_after,
                created_before=created_before,
            )

            rows = self._session.execute(
                statement.order_by(
                    relevance_score.desc(),
                    SearchDocumentRecord.created_at.asc(),
                )
                .limit(limit)
                .offset(offset)
            ).all()

            return [
                RankedSearchDocument(
                    search_document=self._document_to_domain(record),
                    relevance_score=float(score),
                )
                for record, score in rows
            ]

    def _document_to_domain(self, record: SearchDocumentRecord) -> SearchDocument:
        return SearchDocument(
            id=SearchDocumentId(record.id),
            workspace_id=WorkspaceId(record.workspace_id),
            knowledge_item_id=record.knowledge_item_id,
            document_id=record.document_id,
            document_version_id=record.document_version_id,
            source_type=record.source_type,
            mime_type=record.mime_type,
            searchable_text=record.searchable_text,
            created_at=_as_utc(record.created_at),
            updated_at=_as_utc(record.updated_at),
        )

    def _document_to_record(self, search_document: SearchDocument) -> SearchDocumentRecord:
        return SearchDocumentRecord(
            id=search_document.id.value,
            workspace_id=search_document.workspace_id.value,
            knowledge_item_id=search_document.knowledge_item_id,
            document_id=search_document.document_id,
            document_version_id=search_document.document_version_id,
            source_type=search_document.source_type,
            mime_type=search_document.mime_type,
            searchable_text=search_document.searchable_text,
            search_vector=_search_vector_expression(
                self._session,
                search_document.searchable_text,
            ),
            created_at=search_document.created_at,
            updated_at=search_document.updated_at,
        )


def _apply_search_filters(
    statement: Select[tuple[SearchDocumentRecord, float]],
    *,
    document_id: str | None,
    document_version_id: str | None,
    source_type: str | None,
    mime_type: str | None,
    created_after: datetime | None,
    created_before: datetime | None,
) -> Select[tuple[SearchDocumentRecord, float]]:
    if document_id is not None:
        statement = statement.where(SearchDocumentRecord.document_id == document_id)
    if document_version_id is not None:
        statement = statement.where(
            SearchDocumentRecord.document_version_id == document_version_id,
        )
    if source_type is not None:
        statement = statement.where(SearchDocumentRecord.source_type == source_type)
    if mime_type is not None:
        statement = statement.where(SearchDocumentRecord.mime_type == mime_type)
    if created_after is not None:
        statement = statement.where(SearchDocumentRecord.created_at >= created_after)
    if created_before is not None:
        statement = statement.where(SearchDocumentRecord.created_at <= created_before)
    return statement


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _supports_full_text_search(session: OrmSession) -> bool:
    try:
        bind = session.get_bind()
    except Exception:
        return False
    return bind.dialect.name == "postgresql"


def _search_vector_expression(session: OrmSession, searchable_text: str) -> object:
    if _supports_full_text_search(session):
        return func.to_tsvector(ENGLISH_TEXT_SEARCH_CONFIG, searchable_text)
    return searchable_text
