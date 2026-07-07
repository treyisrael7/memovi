from datetime import UTC, datetime

from sqlalchemy.orm import Session as OrmSession

from documents.domain.entities import Document, DocumentVersion
from documents.domain.value_objects import DocumentId, DocumentName, MimeType, SourceType
from documents.infrastructure.persistence.models import DocumentRecord, DocumentVersionRecord


class SqlAlchemyDocumentRepository:
    def __init__(self, session: OrmSession) -> None:
        self._session = session

    def get_by_id(self, document_id: DocumentId) -> Document | None:
        record = self._session.get(DocumentRecord, document_id.value)
        if record is None:
            return None
        return self._to_domain(record)

    def add(self, document: Document) -> None:
        self._session.add(
            DocumentRecord(
                id=document.id.value,
                name=document.name.value,
                mime_type=document.mime_type.value,
                source_type=document.source_type.value,
                created_at=document.created_at,
            )
        )

    def list_all(self) -> list[Document]:
        records = (
            self._session.query(DocumentRecord).order_by(DocumentRecord.created_at.desc()).all()
        )
        return [self._to_domain(record) for record in records]

    def add_version(self, version: DocumentVersion) -> None:
        self._session.add(
            DocumentVersionRecord(
                id=version.id,
                document_id=version.document_id.value,
                version_number=version.version_number,
                storage_key=version.storage_key,
                normalized_content=version.normalized_content,
                created_at=version.created_at,
            )
        )

    def get_version_by_id(self, version_id: str) -> DocumentVersion | None:
        record = self._session.get(DocumentVersionRecord, version_id)
        if record is None:
            return None
        return self._version_to_domain(record)

    def save_version(self, version: DocumentVersion) -> None:
        record = self._session.get(DocumentVersionRecord, version.id)
        if record is None:
            raise ValueError(f"Document version '{version.id}' was not found.")

        record.normalized_content = version.normalized_content

    def get_latest_version(self, document_id: DocumentId) -> DocumentVersion | None:
        record = (
            self._session.query(DocumentVersionRecord)
            .filter(DocumentVersionRecord.document_id == document_id.value)
            .order_by(DocumentVersionRecord.version_number.desc())
            .first()
        )
        if record is None:
            return None
        return self._version_to_domain(record)

    def _to_domain(self, record: DocumentRecord) -> Document:
        return Document(
            id=DocumentId(record.id),
            name=DocumentName(record.name),
            mime_type=MimeType(record.mime_type),
            source_type=SourceType(record.source_type),
            created_at=_as_utc(record.created_at),
        )

    def _version_to_domain(self, record: DocumentVersionRecord) -> DocumentVersion:
        return DocumentVersion(
            id=record.id,
            document_id=DocumentId(record.document_id),
            version_number=record.version_number,
            storage_key=record.storage_key,
            normalized_content=record.normalized_content,
            created_at=_as_utc(record.created_at),
        )


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
