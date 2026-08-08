from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime

from memovi_memory.domain.entities import Tag, TagAssignment
from memovi_memory.domain.value_objects import CollectionMemberKind


@dataclass(frozen=True, slots=True)
class TagDto:
    id: str
    workspace_id: str
    name: str
    color: str | None
    description: str
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_tag(cls, tag: Tag) -> TagDto:
        return cls(
            id=tag.id.value,
            workspace_id=tag.workspace_id.value,
            name=tag.name,
            color=tag.color,
            description=tag.description,
            created_at=tag.created_at,
            updated_at=tag.updated_at,
        )


@dataclass(frozen=True, slots=True)
class TagAssignmentDto:
    id: str
    tag_id: str
    member_kind: str
    member_id: str
    assigned_at: datetime

    @classmethod
    def from_assignment(cls, assignment: TagAssignment) -> TagAssignmentDto:
        return cls(
            id=assignment.id,
            tag_id=assignment.tag_id.value,
            member_kind=assignment.member_kind.value,
            member_id=assignment.member_id,
            assigned_at=assignment.assigned_at,
        )


@dataclass(frozen=True, slots=True)
class TagListItemDto:
    """Tag row with assignment counts for list views."""

    id: str
    workspace_id: str
    name: str
    color: str | None
    description: str
    created_at: datetime
    updated_at: datetime
    assignment_count: int
    counts_by_kind: Mapping[str, int]

    @classmethod
    def from_tag_and_counts(
        cls,
        tag: Tag,
        *,
        counts_by_kind: Mapping[str, int],
    ) -> TagListItemDto:
        return cls(
            id=tag.id.value,
            workspace_id=tag.workspace_id.value,
            name=tag.name,
            color=tag.color,
            description=tag.description,
            created_at=tag.created_at,
            updated_at=tag.updated_at,
            assignment_count=sum(counts_by_kind.values()),
            counts_by_kind=dict(counts_by_kind),
        )


def empty_tag_counts() -> dict[str, int]:
    return {kind.value: 0 for kind in CollectionMemberKind}
