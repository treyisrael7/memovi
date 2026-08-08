from collections.abc import Callable, Sequence
from datetime import UTC, datetime

from memovi_shared import WorkspaceId

from memovi_memory.application.dto.tag_dto import (
    TagAssignmentDto,
    TagDto,
    TagListItemDto,
    empty_tag_counts,
)
from memovi_memory.domain.entities import Tag, TagAssignment
from memovi_memory.domain.events import (
    TagAssigned,
    TagCreated,
    TagDeleted,
    TagUnassigned,
    TagUpdated,
)
from memovi_memory.domain.exceptions import (
    DuplicateTagAssignmentError,
    DuplicateTagNameError,
    InvalidTagIdError,
    TagAssignmentNotFoundError,
    TagNotFoundError,
)
from memovi_memory.domain.repositories import TagRepository
from memovi_memory.domain.value_objects import (
    CollectionMemberKind,
    TagId,
    parse_member_kind,
)

EventPublisher = Callable[[object], None]
_COLOR_UNSET: object = object()


class TagService:
    """Application service for knowledge organization via tags."""

    def __init__(
        self,
        *,
        repository: TagRepository,
        publish: EventPublisher | None = None,
    ) -> None:
        self._repository = repository
        self._publish = publish

    def create(
        self,
        *,
        workspace_id: WorkspaceId,
        name: str,
        color: str | None = None,
        description: str = "",
        now: datetime | None = None,
    ) -> TagDto:
        timestamp = now or datetime.now(UTC)
        tag = Tag.create(
            workspace_id=workspace_id,
            name=name,
            color=color,
            description=description,
            now=timestamp,
        )
        self._ensure_unique_name(tag.name_key, workspace_id=workspace_id)
        self._repository.add(tag)
        self._emit(
            TagCreated(
                tag_id=tag.id.value,
                workspace_id=workspace_id,
                name=tag.name,
                occurred_at=timestamp,
            )
        )
        return TagDto.from_tag(tag)

    def update(
        self,
        tag_id: str,
        *,
        workspace_id: WorkspaceId,
        name: str | None = None,
        color: str | None | object = _COLOR_UNSET,
        description: str | None = None,
        now: datetime | None = None,
    ) -> TagDto:
        tag = self._require_tag(tag_id, workspace_id=workspace_id)
        timestamp = now or datetime.now(UTC)
        updated = tag
        if name is not None:
            updated = updated.rename(name, now=timestamp)
            if updated.name_key != tag.name_key:
                self._ensure_unique_name(
                    updated.name_key,
                    workspace_id=workspace_id,
                    exclude_tag_id=tag.id,
                )
        if color is not _COLOR_UNSET:
            color_value = color if isinstance(color, str) else None
            updated = updated.update_color(color_value, now=timestamp)
        if description is not None:
            updated = updated.update_description(description, now=timestamp)
        if updated is tag:
            return TagDto.from_tag(tag)

        self._repository.save(updated)
        self._emit(
            TagUpdated(
                tag_id=updated.id.value,
                workspace_id=workspace_id,
                name=updated.name,
                occurred_at=timestamp,
            )
        )
        return TagDto.from_tag(updated)

    def delete(
        self,
        tag_id: str,
        *,
        workspace_id: WorkspaceId,
        now: datetime | None = None,
    ) -> None:
        tag = self._require_tag(tag_id, workspace_id=workspace_id)
        deleted = self._repository.delete(tag.id, workspace_id=workspace_id)
        if not deleted:
            raise TagNotFoundError(f"Tag {tag_id} was not found.")
        timestamp = now or datetime.now(UTC)
        self._emit(
            TagDeleted(
                tag_id=tag.id.value,
                workspace_id=workspace_id,
                occurred_at=timestamp,
            )
        )

    def get(self, tag_id: str, *, workspace_id: WorkspaceId) -> TagDto:
        return TagDto.from_tag(self._require_tag(tag_id, workspace_id=workspace_id))

    def list(self, *, workspace_id: WorkspaceId) -> Sequence[TagListItemDto]:
        tags = self._repository.list_by_workspace(workspace_id=workspace_id)
        items: list[TagListItemDto] = []
        for tag in tags:
            counts = empty_tag_counts()
            counts.update(
                self._repository.count_assignments_by_kind(
                    tag.id,
                    workspace_id=workspace_id,
                )
            )
            items.append(TagListItemDto.from_tag_and_counts(tag, counts_by_kind=counts))
        return items

    def suggest(
        self,
        *,
        workspace_id: WorkspaceId,
        query: str,
        limit: int = 20,
    ) -> Sequence[TagDto]:
        tags = self._repository.suggest_by_prefix(
            workspace_id=workspace_id,
            prefix=query,
            limit=limit,
        )
        return tuple(TagDto.from_tag(tag) for tag in tags)

    def list_for_target(
        self,
        *,
        workspace_id: WorkspaceId,
        member_kind: str,
        member_id: str,
    ) -> Sequence[TagDto]:
        kind = parse_member_kind(member_kind)
        tags = self._repository.list_tags_for_member(
            workspace_id=workspace_id,
            member_kind=kind,
            member_id=member_id.strip(),
        )
        return tuple(TagDto.from_tag(tag) for tag in tags)

    def list_assignments(
        self,
        tag_id: str,
        *,
        workspace_id: WorkspaceId,
        member_kind: str | None = None,
        query: str | None = None,
    ) -> Sequence[TagAssignmentDto]:
        tag = self._require_tag(tag_id, workspace_id=workspace_id)
        kind = parse_member_kind(member_kind) if member_kind else None
        assignments = self._repository.list_assignments(
            tag.id,
            workspace_id=workspace_id,
            member_kind=kind,
            query=query,
        )
        return tuple(TagAssignmentDto.from_assignment(item) for item in assignments)

    def assign(
        self,
        tag_id: str,
        *,
        workspace_id: WorkspaceId,
        member_kind: str,
        member_id: str,
        now: datetime | None = None,
    ) -> TagAssignmentDto:
        tag = self._require_tag(tag_id, workspace_id=workspace_id)
        kind = parse_member_kind(member_kind)
        stripped_member_id = member_id.strip()
        existing = self._repository.get_assignment(
            tag_id=tag.id,
            member_kind=kind,
            member_id=stripped_member_id,
            workspace_id=workspace_id,
        )
        if existing is not None:
            raise DuplicateTagAssignmentError(
                f"{kind.value} {stripped_member_id} already has this tag.",
            )

        timestamp = now or datetime.now(UTC)
        assignment = TagAssignment.create(
            tag_id=tag.id,
            member_kind=kind,
            member_id=member_id,
            now=timestamp,
        )
        self._repository.add_assignment(assignment)
        self._repository.save(tag.touch(timestamp))
        self._emit(
            TagAssigned(
                tag_id=tag.id.value,
                workspace_id=workspace_id,
                member_kind=kind.value,
                member_id=assignment.member_id,
                occurred_at=timestamp,
            )
        )
        return TagAssignmentDto.from_assignment(assignment)

    def unassign(
        self,
        tag_id: str,
        *,
        workspace_id: WorkspaceId,
        member_kind: str,
        member_id: str,
        now: datetime | None = None,
    ) -> None:
        tag = self._require_tag(tag_id, workspace_id=workspace_id)
        kind = parse_member_kind(member_kind)
        removed = self._repository.remove_assignment(
            tag_id=tag.id,
            member_kind=kind,
            member_id=member_id.strip(),
            workspace_id=workspace_id,
        )
        if removed is None:
            raise TagAssignmentNotFoundError(
                f"{kind.value} {member_id.strip()} does not have this tag.",
            )

        timestamp = now or datetime.now(UTC)
        self._repository.save(tag.touch(timestamp))
        self._emit(
            TagUnassigned(
                tag_id=tag.id.value,
                workspace_id=workspace_id,
                member_kind=kind.value,
                member_id=removed.member_id,
                occurred_at=timestamp,
            )
        )

    def resolve_search_member_ids(
        self,
        tag_ids: Sequence[str],
        *,
        workspace_id: WorkspaceId,
    ) -> tuple[frozenset[str], frozenset[str]]:
        """Return (document_ids, knowledge_item_ids) for search filtering.

        Multiple tags use AND semantics: document sets and knowledge sets are
        each intersected across the requested tags.
        """
        if not tag_ids:
            return frozenset(), frozenset()

        document_sets: list[frozenset[str]] = []
        knowledge_sets: list[frozenset[str]] = []
        for raw_tag_id in tag_ids:
            tag = self._require_tag(raw_tag_id, workspace_id=workspace_id)
            grouped = self._repository.member_ids_for_kinds(
                tag.id,
                workspace_id=workspace_id,
                kinds=(CollectionMemberKind.DOCUMENT, CollectionMemberKind.KNOWLEDGE),
            )
            document_sets.append(grouped.get(CollectionMemberKind.DOCUMENT, frozenset()))
            knowledge_sets.append(grouped.get(CollectionMemberKind.KNOWLEDGE, frozenset()))

        document_ids = document_sets[0]
        knowledge_ids = knowledge_sets[0]
        for docs, knowledge in zip(document_sets[1:], knowledge_sets[1:], strict=True):
            document_ids = document_ids & docs
            knowledge_ids = knowledge_ids & knowledge
        return document_ids, knowledge_ids

    def _ensure_unique_name(
        self,
        name_key: str,
        *,
        workspace_id: WorkspaceId,
        exclude_tag_id: TagId | None = None,
    ) -> None:
        existing = self._repository.get_by_name_key(name_key, workspace_id=workspace_id)
        if existing is None:
            return
        if exclude_tag_id is not None and existing.id == exclude_tag_id:
            return
        raise DuplicateTagNameError(f"A tag named “{existing.name}” already exists.")

    def _require_tag(self, tag_id: str, *, workspace_id: WorkspaceId) -> Tag:
        try:
            parsed_id = TagId(tag_id)
        except InvalidTagIdError as exc:
            raise TagNotFoundError(f"Tag {tag_id} was not found.") from exc
        tag = self._repository.get_by_id(parsed_id, workspace_id=workspace_id)
        if tag is None:
            raise TagNotFoundError(f"Tag {tag_id} was not found.")
        return tag

    def _emit(self, event: object) -> None:
        if self._publish is not None:
            self._publish(event)
