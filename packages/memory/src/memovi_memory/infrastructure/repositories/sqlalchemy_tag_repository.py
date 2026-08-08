from collections.abc import Sequence
from datetime import UTC, datetime

from memovi_observability import timed_operation
from memovi_shared import WorkspaceId
from sqlalchemy import func
from sqlalchemy.orm import Session as OrmSession

from memovi_memory.domain.entities import Tag, TagAssignment
from memovi_memory.domain.value_objects import CollectionMemberKind, TagId, parse_member_kind
from memovi_memory.infrastructure.persistence.models import TagAssignmentRecord, TagRecord

_REPO = "SqlAlchemyTagRepository"


class SqlAlchemyTagRepository:
    def __init__(self, session: OrmSession) -> None:
        self._session = session

    def add(self, tag: Tag) -> None:
        with timed_operation("repository.add", repository=_REPO):
            self._session.add(self._to_tag_record(tag))

    def save(self, tag: Tag) -> None:
        with timed_operation("repository.save", repository=_REPO):
            record = (
                self._session.query(TagRecord)
                .filter(
                    TagRecord.id == tag.id.value,
                    TagRecord.workspace_id == tag.workspace_id.value,
                )
                .one_or_none()
            )
            if record is None:
                self._session.add(self._to_tag_record(tag))
                return
            record.name = tag.name
            record.name_key = tag.name_key
            record.color = tag.color
            record.description = tag.description
            record.updated_at = tag.updated_at

    def get_by_id(self, tag_id: TagId, *, workspace_id: WorkspaceId) -> Tag | None:
        with timed_operation("repository.get_by_id", repository=_REPO):
            record = (
                self._session.query(TagRecord)
                .filter(
                    TagRecord.id == tag_id.value,
                    TagRecord.workspace_id == workspace_id.value,
                )
                .one_or_none()
            )
            if record is None:
                return None
            return self._to_tag(record)

    def get_by_name_key(self, name_key: str, *, workspace_id: WorkspaceId) -> Tag | None:
        record = (
            self._session.query(TagRecord)
            .filter(
                TagRecord.name_key == name_key,
                TagRecord.workspace_id == workspace_id.value,
            )
            .one_or_none()
        )
        if record is None:
            return None
        return self._to_tag(record)

    def list_by_workspace(self, *, workspace_id: WorkspaceId) -> Sequence[Tag]:
        with timed_operation("repository.list_by_workspace", repository=_REPO):
            records = (
                self._session.query(TagRecord)
                .filter(TagRecord.workspace_id == workspace_id.value)
                .order_by(func.lower(TagRecord.name).asc(), TagRecord.created_at.asc())
                .all()
            )
            return [self._to_tag(record) for record in records]

    def suggest_by_prefix(
        self,
        *,
        workspace_id: WorkspaceId,
        prefix: str,
        limit: int = 20,
    ) -> Sequence[Tag]:
        needle = prefix.strip().casefold()
        query = self._session.query(TagRecord).filter(TagRecord.workspace_id == workspace_id.value)
        if needle:
            query = query.filter(TagRecord.name_key.startswith(needle))
        records = (
            query.order_by(func.lower(TagRecord.name).asc(), TagRecord.created_at.asc())
            .limit(max(1, limit))
            .all()
        )
        return [self._to_tag(record) for record in records]

    def delete(self, tag_id: TagId, *, workspace_id: WorkspaceId) -> bool:
        with timed_operation("repository.delete", repository=_REPO):
            record = (
                self._session.query(TagRecord)
                .filter(
                    TagRecord.id == tag_id.value,
                    TagRecord.workspace_id == workspace_id.value,
                )
                .one_or_none()
            )
            if record is None:
                return False
            self._session.query(TagAssignmentRecord).filter(
                TagAssignmentRecord.tag_id == tag_id.value,
            ).delete(synchronize_session=False)
            self._session.delete(record)
            return True

    def add_assignment(self, assignment: TagAssignment) -> None:
        with timed_operation("repository.add_assignment", repository=_REPO):
            tag = (
                self._session.query(TagRecord).filter(TagRecord.id == assignment.tag_id.value).one()
            )
            self._session.add(
                TagAssignmentRecord(
                    id=assignment.id,
                    tag_id=assignment.tag_id.value,
                    workspace_id=tag.workspace_id,
                    member_kind=assignment.member_kind.value,
                    member_id=assignment.member_id,
                    assigned_at=assignment.assigned_at,
                )
            )

    def get_assignment(
        self,
        *,
        tag_id: TagId,
        member_kind: CollectionMemberKind,
        member_id: str,
        workspace_id: WorkspaceId,
    ) -> TagAssignment | None:
        record = (
            self._session.query(TagAssignmentRecord)
            .filter(
                TagAssignmentRecord.tag_id == tag_id.value,
                TagAssignmentRecord.workspace_id == workspace_id.value,
                TagAssignmentRecord.member_kind == member_kind.value,
                TagAssignmentRecord.member_id == member_id,
            )
            .one_or_none()
        )
        if record is None:
            return None
        return self._to_assignment(record)

    def list_assignments(
        self,
        tag_id: TagId,
        *,
        workspace_id: WorkspaceId,
        member_kind: CollectionMemberKind | None = None,
        query: str | None = None,
    ) -> Sequence[TagAssignment]:
        filters = [
            TagAssignmentRecord.tag_id == tag_id.value,
            TagAssignmentRecord.workspace_id == workspace_id.value,
        ]
        if member_kind is not None:
            filters.append(TagAssignmentRecord.member_kind == member_kind.value)
        records = (
            self._session.query(TagAssignmentRecord)
            .filter(*filters)
            .order_by(TagAssignmentRecord.assigned_at.desc())
            .all()
        )
        assignments = [self._to_assignment(record) for record in records]
        if query:
            needle = query.strip().lower()
            if needle:
                assignments = [
                    item
                    for item in assignments
                    if needle in item.member_id.lower() or needle in item.member_kind.value
                ]
        return assignments

    def list_tags_for_member(
        self,
        *,
        workspace_id: WorkspaceId,
        member_kind: CollectionMemberKind,
        member_id: str,
    ) -> Sequence[Tag]:
        records = (
            self._session.query(TagRecord)
            .join(TagAssignmentRecord, TagAssignmentRecord.tag_id == TagRecord.id)
            .filter(
                TagRecord.workspace_id == workspace_id.value,
                TagAssignmentRecord.workspace_id == workspace_id.value,
                TagAssignmentRecord.member_kind == member_kind.value,
                TagAssignmentRecord.member_id == member_id,
            )
            .order_by(func.lower(TagRecord.name).asc(), TagRecord.created_at.asc())
            .all()
        )
        return [self._to_tag(record) for record in records]

    def remove_assignment(
        self,
        *,
        tag_id: TagId,
        member_kind: CollectionMemberKind,
        member_id: str,
        workspace_id: WorkspaceId,
    ) -> TagAssignment | None:
        record = (
            self._session.query(TagAssignmentRecord)
            .filter(
                TagAssignmentRecord.tag_id == tag_id.value,
                TagAssignmentRecord.workspace_id == workspace_id.value,
                TagAssignmentRecord.member_kind == member_kind.value,
                TagAssignmentRecord.member_id == member_id,
            )
            .one_or_none()
        )
        if record is None:
            return None
        assignment = self._to_assignment(record)
        self._session.delete(record)
        return assignment

    def count_assignments_by_kind(
        self,
        tag_id: TagId,
        *,
        workspace_id: WorkspaceId,
    ) -> dict[str, int]:
        rows = (
            self._session.query(
                TagAssignmentRecord.member_kind,
                func.count(TagAssignmentRecord.id),
            )
            .filter(
                TagAssignmentRecord.tag_id == tag_id.value,
                TagAssignmentRecord.workspace_id == workspace_id.value,
            )
            .group_by(TagAssignmentRecord.member_kind)
            .all()
        )
        return {kind: int(count) for kind, count in rows}

    def member_ids_for_kinds(
        self,
        tag_id: TagId,
        *,
        workspace_id: WorkspaceId,
        kinds: Sequence[CollectionMemberKind],
    ) -> dict[CollectionMemberKind, frozenset[str]]:
        kind_values = [kind.value for kind in kinds]
        records = (
            self._session.query(TagAssignmentRecord)
            .filter(
                TagAssignmentRecord.tag_id == tag_id.value,
                TagAssignmentRecord.workspace_id == workspace_id.value,
                TagAssignmentRecord.member_kind.in_(kind_values),
            )
            .all()
        )
        grouped: dict[CollectionMemberKind, set[str]] = {kind: set() for kind in kinds}
        for record in records:
            kind = parse_member_kind(record.member_kind)
            if kind in grouped:
                grouped[kind].add(record.member_id)
        return {kind: frozenset(ids) for kind, ids in grouped.items()}

    @staticmethod
    def _to_tag_record(tag: Tag) -> TagRecord:
        return TagRecord(
            id=tag.id.value,
            workspace_id=tag.workspace_id.value,
            name=tag.name,
            name_key=tag.name_key,
            color=tag.color,
            description=tag.description,
            created_at=tag.created_at,
            updated_at=tag.updated_at,
        )

    @staticmethod
    def _to_tag(record: TagRecord) -> Tag:
        return Tag(
            id=TagId(record.id),
            workspace_id=WorkspaceId(record.workspace_id),
            name=record.name,
            name_key=record.name_key,
            color=record.color,
            description=record.description or "",
            created_at=_ensure_aware(record.created_at),
            updated_at=_ensure_aware(record.updated_at),
        )

    @staticmethod
    def _to_assignment(record: TagAssignmentRecord) -> TagAssignment:
        return TagAssignment(
            id=record.id,
            tag_id=TagId(record.tag_id),
            member_kind=parse_member_kind(record.member_kind),
            member_id=record.member_id,
            assigned_at=_ensure_aware(record.assigned_at),
        )


def _ensure_aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value
