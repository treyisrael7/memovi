from dataclasses import dataclass, replace
from datetime import UTC, datetime

from memovi_shared import WorkspaceId

from memovi_memory.domain.exceptions import InvalidTagError
from memovi_memory.domain.value_objects import TagId

_MAX_NAME_LENGTH = 256
_MAX_DESCRIPTION_LENGTH = 4000
_MAX_COLOR_LENGTH = 64


@dataclass(frozen=True, slots=True)
class Tag:
    """User-owned organizational label within a workspace.

    Tags label references to Documents, Knowledge, Conversations, and Workflows.
    They do not store knowledge content or participate in ingestion. Names are
    unique per workspace case-insensitively via ``name_key``.
    """

    id: TagId
    workspace_id: WorkspaceId
    name: str
    name_key: str
    color: str | None
    description: str
    created_at: datetime
    updated_at: datetime

    def __post_init__(self) -> None:
        if self.updated_at < self.created_at:
            raise InvalidTagError("Updated timestamp cannot precede created timestamp.")

    @classmethod
    def create(
        cls,
        *,
        workspace_id: WorkspaceId,
        name: str,
        color: str | None = None,
        description: str = "",
        tag_id: TagId | None = None,
        now: datetime | None = None,
    ) -> Tag:
        display_name, name_key = normalize_tag_name(name)
        timestamp = now or datetime.now(UTC)
        return cls(
            id=tag_id or TagId.new(),
            workspace_id=workspace_id,
            name=display_name,
            name_key=name_key,
            color=normalize_tag_color(color),
            description=normalize_tag_description(description),
            created_at=timestamp,
            updated_at=timestamp,
        )

    def rename(self, name: str, *, now: datetime | None = None) -> Tag:
        display_name, name_key = normalize_tag_name(name)
        return replace(
            self,
            name=display_name,
            name_key=name_key,
            updated_at=now or datetime.now(UTC),
        )

    def update_color(self, color: str | None, *, now: datetime | None = None) -> Tag:
        return replace(
            self,
            color=normalize_tag_color(color),
            updated_at=now or datetime.now(UTC),
        )

    def update_description(self, description: str, *, now: datetime | None = None) -> Tag:
        return replace(
            self,
            description=normalize_tag_description(description),
            updated_at=now or datetime.now(UTC),
        )

    def touch(self, now: datetime | None = None) -> Tag:
        return replace(self, updated_at=now or datetime.now(UTC))


def normalize_tag_name(name: str) -> tuple[str, str]:
    display_name = name.strip()
    if not display_name:
        raise InvalidTagError("Tag name is required.")
    if len(display_name) > _MAX_NAME_LENGTH:
        raise InvalidTagError(f"Tag name must be at most {_MAX_NAME_LENGTH} characters.")
    return display_name, display_name.casefold()


def normalize_tag_color(color: str | None) -> str | None:
    if color is None:
        return None
    normalized = color.strip()
    if not normalized:
        return None
    if len(normalized) > _MAX_COLOR_LENGTH:
        raise InvalidTagError(f"Tag color must be at most {_MAX_COLOR_LENGTH} characters.")
    return normalized


def normalize_tag_description(description: str) -> str:
    normalized = description.strip()
    if len(normalized) > _MAX_DESCRIPTION_LENGTH:
        raise InvalidTagError(
            f"Tag description must be at most {_MAX_DESCRIPTION_LENGTH} characters.",
        )
    return normalized
