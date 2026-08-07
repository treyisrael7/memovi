from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType

from memovi_shared import WorkspaceId

from memovi_connectors.domain.exceptions import InvalidConnectorError

_SYNC_MODES = frozenset({"initial", "incremental"})


@dataclass(frozen=True, slots=True)
class ConnectorExecutionContext:
    """Runtime context for a connector synchronization run.

    Carries workspace ownership and correlation identifiers. Credential values
    are never stored on the context; connectors resolve :class:`AuthCredentialRef`
    through infrastructure at the composition root.
    """

    workspace_id: WorkspaceId
    connector_id: str
    sync_mode: str = "incremental"
    correlation_id: str | None = None
    cursor: str | None = None
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.workspace_id, WorkspaceId):
            raise InvalidConnectorError(
                "Connector execution context workspace_id must be a WorkspaceId.",
            )
        connector_id = self.connector_id.strip().lower()
        if not connector_id:
            raise InvalidConnectorError(
                "Connector execution context connector_id is required.",
            )
        sync_mode = self.sync_mode.strip().lower()
        if sync_mode not in _SYNC_MODES:
            raise InvalidConnectorError(
                f"Connector sync_mode must be one of: {', '.join(sorted(_SYNC_MODES))}.",
            )
        cursor = self.cursor.strip() if isinstance(self.cursor, str) else self.cursor
        if isinstance(cursor, str) and not cursor:
            raise InvalidConnectorError(
                "Connector execution context cursor cannot be blank when set.",
            )
        if self.correlation_id is not None:
            correlation_id = self.correlation_id.strip()
            if not correlation_id:
                raise InvalidConnectorError(
                    "correlation_id cannot be blank when provided.",
                )
            object.__setattr__(self, "correlation_id", correlation_id)
        if not isinstance(self.metadata, Mapping):
            raise InvalidConnectorError(
                "Connector execution context metadata must be a mapping.",
            )

        object.__setattr__(self, "connector_id", connector_id)
        object.__setattr__(self, "sync_mode", sync_mode)
        object.__setattr__(self, "cursor", cursor)
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))

    @classmethod
    def create(
        cls,
        *,
        workspace_id: WorkspaceId,
        connector_id: str,
        sync_mode: str = "incremental",
        correlation_id: str | None = None,
        cursor: str | None = None,
        metadata: Mapping[str, object] | None = None,
    ) -> ConnectorExecutionContext:
        return cls(
            workspace_id=workspace_id,
            connector_id=connector_id,
            sync_mode=sync_mode,
            correlation_id=correlation_id,
            cursor=cursor,
            metadata={} if metadata is None else metadata,
        )
