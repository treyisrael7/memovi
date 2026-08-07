from typing import Protocol

from memovi_connectors.domain.value_objects import (
    ConnectorConfiguration,
    ConnectorExecutionContext,
    ConnectorHealth,
    ConnectorMetadata,
    ConnectorResult,
    NormalizedImportItem,
)


class DocumentImportPort(Protocol):
    """Handoff from connectors into the Documents domain.

    Implementations live at the composition root and call Documents ingest /
    create use cases. Connectors must not store documents themselves.
    """

    def import_item(self, item: NormalizedImportItem) -> str:
        """Import one normalized item and return the Documents document id.

        For ``change_kind=delete``, implementations should remove or tombstone
        the matching document and may return an empty string when nothing matched.
        """
        raise NotImplementedError


class Connector(Protocol):
    """Provider-neutral interface for external knowledge acquisition.

    Implementations may use vendor SDKs internally but must not leak SDK types
    through this contract. Sync outcomes are normalized into documents via
    :class:`DocumentImportPort` — never a parallel knowledge store.
    """

    def connector_id(self) -> str:
        """Stable connector identifier (e.g. github, fake)."""
        raise NotImplementedError

    def metadata(self) -> ConnectorMetadata:
        """Return discovery metadata for this connector type."""
        raise NotImplementedError

    def configuration(self) -> ConnectorConfiguration:
        """Return configuration (no secret values)."""
        raise NotImplementedError

    def health(self) -> ConnectorHealth:
        """Return a normalized health / sync status snapshot."""
        raise NotImplementedError

    def sync(self, context: ConnectorExecutionContext) -> ConnectorResult:
        """Run an initial or incremental synchronization.

        Successful syncs produce normalized import items and hand them to the
        configured :class:`DocumentImportPort`. Expected failures should be
        returned as failed :class:`ConnectorResult` values.
        """
        raise NotImplementedError
