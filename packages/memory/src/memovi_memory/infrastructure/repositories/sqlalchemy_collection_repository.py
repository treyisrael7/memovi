from collections.abc import Sequence
from datetime import UTC, datetime

from memovi_observability import timed_operation
from memovi_shared import WorkspaceId
from sqlalchemy import func
from sqlalchemy.orm import Session as OrmSession

from memovi_memory.domain.entities import Collection, CollectionActivity, CollectionMembership
from memovi_memory.domain.value_objects import (
    CollectionId,
    CollectionMemberKind,
    CollectionMetadata,
    parse_member_kind,
)
from memovi_memory.infrastructure.persistence.models import (
    CollectionActivityRecord,
    CollectionMembershipRecord,
    CollectionRecord,
)

_REPO = "SqlAlchemyCollectionRepository"


class SqlAlchemyCollectionRepository:
    def __init__(self, session: OrmSession) -> None:
        self._session = session

    def add(self, collection: Collection) -> None:
        with timed_operation("repository.add", repository=_REPO):
            self._session.add(self._to_collection_record(collection))

    def save(self, collection: Collection) -> None:
        with timed_operation("repository.save", repository=_REPO):
            record = (
                self._session.query(CollectionRecord)
                .filter(
                    CollectionRecord.id == collection.id.value,
                    CollectionRecord.workspace_id == collection.workspace_id.value,
                )
                .one_or_none()
            )
            if record is None:
                self._session.add(self._to_collection_record(collection))
                return
            record.name = collection.metadata.name
            record.description = collection.metadata.description
            record.updated_at = collection.updated_at

    def get_by_id(
        self,
        collection_id: CollectionId,
        *,
        workspace_id: WorkspaceId,
    ) -> Collection | None:
        with timed_operation("repository.get_by_id", repository=_REPO):
            record = (
                self._session.query(CollectionRecord)
                .filter(
                    CollectionRecord.id == collection_id.value,
                    CollectionRecord.workspace_id == workspace_id.value,
                )
                .one_or_none()
            )
            if record is None:
                return None
            return self._to_collection(record)

    def list_by_workspace(self, *, workspace_id: WorkspaceId) -> Sequence[Collection]:
        with timed_operation("repository.list_by_workspace", repository=_REPO):
            records = (
                self._session.query(CollectionRecord)
                .filter(CollectionRecord.workspace_id == workspace_id.value)
                .order_by(
                    func.lower(CollectionRecord.name).asc(),
                    CollectionRecord.created_at.asc(),
                )
                .all()
            )
            return [self._to_collection(record) for record in records]

    def delete(
        self,
        collection_id: CollectionId,
        *,
        workspace_id: WorkspaceId,
    ) -> bool:
        with timed_operation("repository.delete", repository=_REPO):
            record = (
                self._session.query(CollectionRecord)
                .filter(
                    CollectionRecord.id == collection_id.value,
                    CollectionRecord.workspace_id == workspace_id.value,
                )
                .one_or_none()
            )
            if record is None:
                return False
            self._session.query(CollectionMembershipRecord).filter(
                CollectionMembershipRecord.collection_id == collection_id.value,
            ).delete(synchronize_session=False)
            self._session.query(CollectionActivityRecord).filter(
                CollectionActivityRecord.collection_id == collection_id.value,
            ).delete(synchronize_session=False)
            self._session.delete(record)
            return True

    def add_membership(self, membership: CollectionMembership) -> None:
        with timed_operation("repository.add_membership", repository=_REPO):
            collection = (
                self._session.query(CollectionRecord)
                .filter(CollectionRecord.id == membership.collection_id.value)
                .one()
            )
            self._session.add(
                CollectionMembershipRecord(
                    id=membership.id,
                    collection_id=membership.collection_id.value,
                    workspace_id=collection.workspace_id,
                    member_kind=membership.member_kind.value,
                    member_id=membership.member_id,
                    reason=membership.reason,
                    added_at=membership.added_at,
                )
            )

    def get_membership(
        self,
        *,
        collection_id: CollectionId,
        member_kind: CollectionMemberKind,
        member_id: str,
        workspace_id: WorkspaceId,
    ) -> CollectionMembership | None:
        record = (
            self._session.query(CollectionMembershipRecord)
            .filter(
                CollectionMembershipRecord.collection_id == collection_id.value,
                CollectionMembershipRecord.workspace_id == workspace_id.value,
                CollectionMembershipRecord.member_kind == member_kind.value,
                CollectionMembershipRecord.member_id == member_id,
            )
            .one_or_none()
        )
        if record is None:
            return None
        return self._to_membership(record)

    def list_memberships(
        self,
        collection_id: CollectionId,
        *,
        workspace_id: WorkspaceId,
        member_kind: CollectionMemberKind | None = None,
        query: str | None = None,
    ) -> Sequence[CollectionMembership]:
        filters = [
            CollectionMembershipRecord.collection_id == collection_id.value,
            CollectionMembershipRecord.workspace_id == workspace_id.value,
        ]
        if member_kind is not None:
            filters.append(CollectionMembershipRecord.member_kind == member_kind.value)
        q = self._session.query(CollectionMembershipRecord).filter(*filters)
        records = q.order_by(CollectionMembershipRecord.added_at.desc()).all()
        memberships = [self._to_membership(record) for record in records]
        if query:
            needle = query.strip().lower()
            if needle:
                memberships = [
                    item
                    for item in memberships
                    if needle in item.member_id.lower()
                    or needle in item.reason.lower()
                    or needle in item.member_kind.value
                ]
        return memberships

    def remove_membership(
        self,
        *,
        collection_id: CollectionId,
        member_kind: CollectionMemberKind,
        member_id: str,
        workspace_id: WorkspaceId,
    ) -> CollectionMembership | None:
        record = (
            self._session.query(CollectionMembershipRecord)
            .filter(
                CollectionMembershipRecord.collection_id == collection_id.value,
                CollectionMembershipRecord.workspace_id == workspace_id.value,
                CollectionMembershipRecord.member_kind == member_kind.value,
                CollectionMembershipRecord.member_id == member_id,
            )
            .one_or_none()
        )
        if record is None:
            return None
        membership = self._to_membership(record)
        self._session.delete(record)
        return membership

    def count_memberships_by_kind(
        self,
        collection_id: CollectionId,
        *,
        workspace_id: WorkspaceId,
    ) -> dict[str, int]:
        rows = (
            self._session.query(
                CollectionMembershipRecord.member_kind,
                func.count(CollectionMembershipRecord.id),
            )
            .filter(
                CollectionMembershipRecord.collection_id == collection_id.value,
                CollectionMembershipRecord.workspace_id == workspace_id.value,
            )
            .group_by(CollectionMembershipRecord.member_kind)
            .all()
        )
        return {kind: int(count) for kind, count in rows}

    def member_ids_for_kinds(
        self,
        collection_id: CollectionId,
        *,
        workspace_id: WorkspaceId,
        kinds: Sequence[CollectionMemberKind],
    ) -> dict[CollectionMemberKind, frozenset[str]]:
        kind_values = [kind.value for kind in kinds]
        records = (
            self._session.query(CollectionMembershipRecord)
            .filter(
                CollectionMembershipRecord.collection_id == collection_id.value,
                CollectionMembershipRecord.workspace_id == workspace_id.value,
                CollectionMembershipRecord.member_kind.in_(kind_values),
            )
            .all()
        )
        grouped: dict[CollectionMemberKind, set[str]] = {kind: set() for kind in kinds}
        for record in records:
            kind = parse_member_kind(record.member_kind)
            if kind in grouped:
                grouped[kind].add(record.member_id)
        return {kind: frozenset(ids) for kind, ids in grouped.items()}

    def add_activity(self, activity: CollectionActivity) -> None:
        self._session.add(
            CollectionActivityRecord(
                id=activity.id,
                collection_id=activity.collection_id.value,
                workspace_id=activity.workspace_id.value,
                activity_type=activity.activity_type,
                member_kind=activity.member_kind.value if activity.member_kind else None,
                member_id=activity.member_id,
                detail=activity.detail,
                occurred_at=activity.occurred_at,
            )
        )

    def list_recent_activity(
        self,
        collection_id: CollectionId,
        *,
        workspace_id: WorkspaceId,
        limit: int = 20,
    ) -> Sequence[CollectionActivity]:
        records = (
            self._session.query(CollectionActivityRecord)
            .filter(
                CollectionActivityRecord.collection_id == collection_id.value,
                CollectionActivityRecord.workspace_id == workspace_id.value,
            )
            .order_by(CollectionActivityRecord.occurred_at.desc())
            .limit(max(1, limit))
            .all()
        )
        return [self._to_activity(record) for record in records]

    @staticmethod
    def _to_collection_record(collection: Collection) -> CollectionRecord:
        return CollectionRecord(
            id=collection.id.value,
            workspace_id=collection.workspace_id.value,
            name=collection.metadata.name,
            description=collection.metadata.description,
            created_at=collection.created_at,
            updated_at=collection.updated_at,
        )

    @staticmethod
    def _to_collection(record: CollectionRecord) -> Collection:
        return Collection(
            id=CollectionId(record.id),
            workspace_id=WorkspaceId(record.workspace_id),
            metadata=CollectionMetadata(name=record.name, description=record.description or ""),
            created_at=_ensure_aware(record.created_at),
            updated_at=_ensure_aware(record.updated_at),
        )

    @staticmethod
    def _to_membership(record: CollectionMembershipRecord) -> CollectionMembership:
        return CollectionMembership(
            id=record.id,
            collection_id=CollectionId(record.collection_id),
            member_kind=parse_member_kind(record.member_kind),
            member_id=record.member_id,
            reason=record.reason,
            added_at=_ensure_aware(record.added_at),
        )

    @staticmethod
    def _to_activity(record: CollectionActivityRecord) -> CollectionActivity:
        return CollectionActivity(
            id=record.id,
            collection_id=CollectionId(record.collection_id),
            workspace_id=WorkspaceId(record.workspace_id),
            activity_type=record.activity_type,
            occurred_at=_ensure_aware(record.occurred_at),
            member_kind=parse_member_kind(record.member_kind) if record.member_kind else None,
            member_id=record.member_id,
            detail=record.detail or "",
        )


def _ensure_aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value
