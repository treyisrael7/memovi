from dataclasses import dataclass
from datetime import datetime

from memovi_shared import WorkspaceId


@dataclass(frozen=True, slots=True)
class TagCreated:
    """Emitted when a tag is created."""

    tag_id: str
    workspace_id: WorkspaceId
    name: str
    occurred_at: datetime


@dataclass(frozen=True, slots=True)
class TagUpdated:
    """Emitted when tag metadata changes."""

    tag_id: str
    workspace_id: WorkspaceId
    name: str
    occurred_at: datetime


@dataclass(frozen=True, slots=True)
class TagDeleted:
    """Emitted when a tag is deleted."""

    tag_id: str
    workspace_id: WorkspaceId
    occurred_at: datetime


@dataclass(frozen=True, slots=True)
class TagAssigned:
    """Emitted when a resource is assigned a tag."""

    tag_id: str
    workspace_id: WorkspaceId
    member_kind: str
    member_id: str
    occurred_at: datetime


@dataclass(frozen=True, slots=True)
class TagUnassigned:
    """Emitted when a tag assignment is removed."""

    tag_id: str
    workspace_id: WorkspaceId
    member_kind: str
    member_id: str
    occurred_at: datetime
