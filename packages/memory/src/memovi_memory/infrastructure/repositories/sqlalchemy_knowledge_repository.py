import builtins
from datetime import UTC, datetime

from memovi_shared import WorkspaceId
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

        record.workspace_id = knowledge_item.workspace_id.value
        record.document_id = knowledge_item.document_id
        record.document_version_id = knowledge_item.document_version_id
        record.source_type = knowledge_item.source_type
        record.mime_type = knowledge_item.mime_type
        record.updated_at = knowledge_item.updated_at

    def get_by_id(
        self,
        knowledge_item_id: KnowledgeItemId,
        *,
        workspace_id: WorkspaceId,
    ) -> KnowledgeItem | None:
        record = (
            self._session.query(KnowledgeItemRecord)
            .filter(
                KnowledgeItemRecord.id == knowledge_item_id.value,
                KnowledgeItemRecord.workspace_id == workspace_id.value,
            )
            .one_or_none()
        )
        if record is None:
            return None
        return self._to_domain(record)

    def list_by_workspace(self, *, workspace_id: WorkspaceId) -> builtins.list[KnowledgeItem]:
        records = (
            self._session.query(KnowledgeItemRecord)
            .filter(KnowledgeItemRecord.workspace_id == workspace_id.value)
            .order_by(KnowledgeItemRecord.created_at.asc())
            .all()
        )
        return [self._to_domain(record) for record in records]

    def list_by_document(
        self,
        *,
        workspace_id: WorkspaceId,
        document_id: str,
    ) -> builtins.list[KnowledgeItem]:
        records = (
            self._session.query(KnowledgeItemRecord)
            .filter(
                KnowledgeItemRecord.workspace_id == workspace_id.value,
                KnowledgeItemRecord.document_id == document_id,
            )
            .order_by(KnowledgeItemRecord.created_at.asc())
            .all()
        )
        return [self._to_domain(record) for record in records]

    def list_by_document_version(
        self,
        *,
        workspace_id: WorkspaceId,
        document_id: str,
        document_version_id: str,
    ) -> builtins.list[KnowledgeItem]:
        records = (
            self._session.query(KnowledgeItemRecord)
            .filter(
                KnowledgeItemRecord.workspace_id == workspace_id.value,
                KnowledgeItemRecord.document_id == document_id,
                KnowledgeItemRecord.document_version_id == document_version_id,
            )
            .order_by(KnowledgeItemRecord.created_at.asc())
            .all()
        )
        return [self._to_domain(record) for record in records]

    def delete(
        self,
        knowledge_item_id: KnowledgeItemId,
        *,
        workspace_id: WorkspaceId,
    ) -> None:
        record = (
            self._session.query(KnowledgeItemRecord)
            .filter(
                KnowledgeItemRecord.id == knowledge_item_id.value,
                KnowledgeItemRecord.workspace_id == workspace_id.value,
            )
            .one_or_none()
        )
        if record is not None:
            self._session.delete(record)

    def _to_domain(self, record: KnowledgeItemRecord) -> KnowledgeItem:
        return KnowledgeItem(
            id=KnowledgeItemId(record.id),
            workspace_id=WorkspaceId(record.workspace_id),
            document_id=record.document_id,
            document_version_id=record.document_version_id,
            source_type=record.source_type,
            mime_type=record.mime_type,
            created_at=_as_utc(record.created_at),
            updated_at=_as_utc(record.updated_at),
        )

    def _to_record(self, knowledge_item: KnowledgeItem) -> KnowledgeItemRecord:
        return KnowledgeItemRecord(
            id=knowledge_item.id.value,
            workspace_id=knowledge_item.workspace_id.value,
            document_id=knowledge_item.document_id,
            document_version_id=knowledge_item.document_version_id,
            source_type=knowledge_item.source_type,
            mime_type=knowledge_item.mime_type,
            created_at=knowledge_item.created_at,
            updated_at=knowledge_item.updated_at,
        )


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
