from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from types import MappingProxyType

from memovi_shared import WorkspaceId

from memovi_connectors.domain.exceptions import InvalidConnectorError


@dataclass(frozen=True, slots=True)
class NormalizedSourceMetadata:
    """Provider-neutral metadata attached to an imported document.

    Downstream Documents / Memory / Search must not need connector-specific
    fields beyond this normalized shape.
    """

    connector_id: str
    external_id: str
    workspace_id: WorkspaceId
    source: str
    owner: str | None = None
    created_at: datetime | None = None
    modified_at: datetime | None = None
    tags: Sequence[str] = ()
    extra: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        connector_id = self.connector_id.strip().lower()
        external_id = self.external_id.strip()
        source = self.source.strip()
        owner = self.owner.strip() if isinstance(self.owner, str) else self.owner

        if not connector_id:
            raise InvalidConnectorError("Normalized source metadata connector_id is required.")
        if not external_id:
            raise InvalidConnectorError("Normalized source metadata external_id is required.")
        if not isinstance(self.workspace_id, WorkspaceId):
            raise InvalidConnectorError(
                "Normalized source metadata workspace_id must be a WorkspaceId.",
            )
        if not source:
            raise InvalidConnectorError("Normalized source metadata source is required.")
        if isinstance(owner, str) and not owner:
            raise InvalidConnectorError(
                "Normalized source metadata owner cannot be blank when set.",
            )
        if not isinstance(self.extra, Mapping):
            raise InvalidConnectorError("Normalized source metadata extra must be a mapping.")

        tags = tuple(tag.strip() for tag in self.tags if tag and tag.strip())
        created_at = self._ensure_aware(self.created_at)
        modified_at = self._ensure_aware(self.modified_at)

        object.__setattr__(self, "connector_id", connector_id)
        object.__setattr__(self, "external_id", external_id)
        object.__setattr__(self, "source", source)
        object.__setattr__(self, "owner", owner)
        object.__setattr__(self, "created_at", created_at)
        object.__setattr__(self, "modified_at", modified_at)
        object.__setattr__(self, "tags", tags)
        object.__setattr__(self, "extra", MappingProxyType(dict(self.extra)))

    @staticmethod
    def _ensure_aware(value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value


@dataclass(frozen=True, slots=True)
class NormalizedImportItem:
    """Content ready to hand to the Documents domain for ingestion.

    Connectors produce these items; Documents owns storage and processing.
    """

    name: str
    mime_type: str
    content: bytes
    metadata: NormalizedSourceMetadata
    change_kind: str = "upsert"
    """One of: upsert, delete, metadata_only."""

    def __post_init__(self) -> None:
        name = self.name.strip()
        mime_type = self.mime_type.strip()
        change_kind = self.change_kind.strip().lower()
        if not name:
            raise InvalidConnectorError("Normalized import item name is required.")
        if not mime_type:
            raise InvalidConnectorError("Normalized import item mime_type is required.")
        if not isinstance(self.metadata, NormalizedSourceMetadata):
            raise InvalidConnectorError(
                "Normalized import item metadata must be NormalizedSourceMetadata.",
            )
        if change_kind not in {"upsert", "delete", "metadata_only"}:
            raise InvalidConnectorError(
                "Normalized import item change_kind must be upsert, delete, or metadata_only.",
            )
        if change_kind == "upsert" and not isinstance(self.content, (bytes, bytearray)):
            raise InvalidConnectorError("Normalized import item content must be bytes.")

        object.__setattr__(self, "name", name)
        object.__setattr__(self, "mime_type", mime_type)
        object.__setattr__(self, "change_kind", change_kind)
        object.__setattr__(self, "content", bytes(self.content))
