from datetime import UTC, datetime

from memovi_observability import timed_operation
from memovi_shared import WorkspaceId
from sqlalchemy.orm import Session as OrmSession

from memovi_memory.domain.entities import ResourceMetadata
from memovi_memory.domain.value_objects import CollectionMemberKind, parse_member_kind
from memovi_memory.infrastructure.persistence.models import ResourceMetadataRecord

_REPO = "SqlAlchemyResourceMetadataRepository"


class SqlAlchemyResourceMetadataRepository:
    def __init__(self, session: OrmSession) -> None:
        self._session = session

    def get(
        self,
        *,
        workspace_id: WorkspaceId,
        member_kind: CollectionMemberKind,
        member_id: str,
    ) -> ResourceMetadata | None:
        with timed_operation("repository.get", repository=_REPO):
            record = (
                self._session.query(ResourceMetadataRecord)
                .filter(
                    ResourceMetadataRecord.workspace_id == workspace_id.value,
                    ResourceMetadataRecord.member_kind == member_kind.value,
                    ResourceMetadataRecord.member_id == member_id,
                )
                .one_or_none()
            )
            if record is None:
                return None
            return self._to_metadata(record)

    def upsert(self, metadata: ResourceMetadata) -> None:
        with timed_operation("repository.upsert", repository=_REPO):
            record = (
                self._session.query(ResourceMetadataRecord)
                .filter(
                    ResourceMetadataRecord.workspace_id == metadata.workspace_id.value,
                    ResourceMetadataRecord.member_kind == metadata.member_kind.value,
                    ResourceMetadataRecord.member_id == metadata.member_id,
                )
                .one_or_none()
            )
            if record is None:
                self._session.add(
                    ResourceMetadataRecord(
                        workspace_id=metadata.workspace_id.value,
                        member_kind=metadata.member_kind.value,
                        member_id=metadata.member_id,
                        title=metadata.title,
                        description=metadata.description,
                        notes=metadata.notes,
                        updated_at=metadata.updated_at,
                    )
                )
                return
            record.title = metadata.title
            record.description = metadata.description
            record.notes = metadata.notes
            record.updated_at = metadata.updated_at

    @staticmethod
    def _to_metadata(record: ResourceMetadataRecord) -> ResourceMetadata:
        return ResourceMetadata(
            workspace_id=WorkspaceId(record.workspace_id),
            member_kind=parse_member_kind(record.member_kind),
            member_id=record.member_id,
            title=record.title,
            description=record.description,
            notes=record.notes,
            updated_at=_ensure_aware(record.updated_at),
        )


def _ensure_aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value
