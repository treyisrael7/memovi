from dataclasses import dataclass
from datetime import datetime

from memovi_shared import WorkspaceId


@dataclass(frozen=True, slots=True)
class CollectionCreated:
    """Emitted when a collection is created."""

    collection_id: str
    workspace_id: WorkspaceId
    name: str
    occurred_at: datetime


@dataclass(frozen=True, slots=True)
class CollectionUpdated:
    """Emitted when collection metadata changes."""

    collection_id: str
    workspace_id: WorkspaceId
    name: str
    occurred_at: datetime


@dataclass(frozen=True, slots=True)
class CollectionDeleted:
    """Emitted when a collection is deleted."""

    collection_id: str
    workspace_id: WorkspaceId
    occurred_at: datetime


@dataclass(frozen=True, slots=True)
class CollectionMemberAdded:
    """Emitted when an item is added to a collection."""

    collection_id: str
    workspace_id: WorkspaceId
    member_kind: str
    member_id: str
    reason: str
    occurred_at: datetime


@dataclass(frozen=True, slots=True)
class CollectionMemberRemoved:
    """Emitted when an item is removed from a collection."""

    collection_id: str
    workspace_id: WorkspaceId
    member_kind: str
    member_id: str
    occurred_at: datetime
