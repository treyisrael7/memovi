import builtins
from datetime import UTC, datetime

from sqlalchemy.orm import Session as OrmSession

from memovi_memory.domain.entities import KnowledgeItem
from memovi_memory.domain.value_objects import KnowledgeItemId
from memovi_memory.infrastructure.persistence.models import KnowledgeItemRecord


class SqlAlchemyKnowledgeRepository:
    def __init__(self, session: OrmSession) -> None:
        self._session = session

    def save(self, knowledge_item: KnowledgeItem) -> None:
        record = self._session.get(KnowledgeItemRecord, knowledge_item.id.value)
        if record is None:
            self._session.add(self._to_record(knowledge_item))
            return

        record.document_id = knowledge_item.document_id
        record.document_version_id = knowledge_item.document_version_id
        record.updated_at = knowledge_item.updated_at

    def get_by_id(self, knowledge_item_id: KnowledgeItemId) -> KnowledgeItem | None:
        record = self._session.get(KnowledgeItemRecord, knowledge_item_id.value)
        if record is None:
            return None
        return self._to_domain(record)

    def list(self) -> builtins.list[KnowledgeItem]:
        records = (
            self._session.query(KnowledgeItemRecord)
            .order_by(KnowledgeItemRecord.created_at.asc())
            .all()
        )
        return [self._to_domain(record) for record in records]

    def list_by_document(self, *, document_id: str) -> builtins.list[KnowledgeItem]:
        records = (
            self._session.query(KnowledgeItemRecord)
            .filter(KnowledgeItemRecord.document_id == document_id)
            .order_by(KnowledgeItemRecord.created_at.asc())
            .all()
        )
        return [self._to_domain(record) for record in records]

    def list_by_document_version(
        self,
        *,
        document_id: str,
        document_version_id: str,
    ) -> builtins.list[KnowledgeItem]:
        records = (
            self._session.query(KnowledgeItemRecord)
            .filter(
                KnowledgeItemRecord.document_id == document_id,
                KnowledgeItemRecord.document_version_id == document_version_id,
            )
            .order_by(KnowledgeItemRecord.created_at.asc())
            .all()
        )
        return [self._to_domain(record) for record in records]

    def delete(self, knowledge_item_id: KnowledgeItemId) -> None:
        record = self._session.get(KnowledgeItemRecord, knowledge_item_id.value)
        if record is not None:
            self._session.delete(record)

    def _to_domain(self, record: KnowledgeItemRecord) -> KnowledgeItem:
        return KnowledgeItem(
            id=KnowledgeItemId(record.id),
            document_id=record.document_id,
            document_version_id=record.document_version_id,
            created_at=_as_utc(record.created_at),
            updated_at=_as_utc(record.updated_at),
        )

    def _to_record(self, knowledge_item: KnowledgeItem) -> KnowledgeItemRecord:
        return KnowledgeItemRecord(
            id=knowledge_item.id.value,
            document_id=knowledge_item.document_id,
            document_version_id=knowledge_item.document_version_id,
            created_at=knowledge_item.created_at,
            updated_at=knowledge_item.updated_at,
        )


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
