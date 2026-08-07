from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from memovi_connectors.domain.value_objects import (
    CONNECTOR_FAKE,
    AuthCredentialRef,
    ConnectorConfiguration,
    ConnectorExecutionContext,
    ConnectorHealth,
    ConnectorMetadata,
    ConnectorResult,
    NormalizedImportItem,
    NormalizedSourceMetadata,
)


class InMemoryDocumentImportPort:
    """Test double that records normalized imports without Documents storage."""

    def __init__(self) -> None:
        self.imported: list[NormalizedImportItem] = []
        self.deleted_external_ids: list[str] = []
        self._ids_by_external: dict[str, str] = {}

    def import_item(self, item: NormalizedImportItem) -> str:
        if item.change_kind == "delete":
            self.deleted_external_ids.append(item.metadata.external_id)
            return self._ids_by_external.pop(item.metadata.external_id, "")
        document_id = self._ids_by_external.get(item.metadata.external_id) or str(uuid4())
        self._ids_by_external[item.metadata.external_id] = document_id
        self.imported.append(item)
        return document_id


class FakeConnector:
    """Deterministic connector for tests and local wiring.

    Produces normalized text documents and hands them to a
    :class:`DocumentImportPort`. Not a production provider adapter.
    """

    def __init__(
        self,
        *,
        connector_id: str = CONNECTOR_FAKE,
        enabled: bool = True,
        healthy: bool = True,
        document_import: InMemoryDocumentImportPort | None = None,
        seed_items: tuple[tuple[str, str], ...] = (("readme.txt", "Fake connector content."),),
    ) -> None:
        self._connector_id = connector_id.strip().lower()
        self._enabled = enabled
        self._healthy = healthy
        self._document_import = document_import or InMemoryDocumentImportPort()
        self._seed_items = seed_items
        self._imported_count = 0
        self._last_synchronized_at: datetime | None = None
        self._last_errors: list[str] = []
        self._pending_changes = len(seed_items)
        self._cursor: str | None = None
        self._config = ConnectorConfiguration(
            connector_id=self._connector_id,
            enabled=enabled,
            auth=AuthCredentialRef(method="none"),
        )
        self._metadata = ConnectorMetadata(
            connector_id=self._connector_id,
            display_name="Fake Connector",
            description="Deterministic connector for tests and local wiring.",
            source_category="other",
            auth_methods=("none",),
            supports_incremental_sync=True,
            supports_delete_detection=True,
        )

    @property
    def document_import(self) -> InMemoryDocumentImportPort:
        return self._document_import

    def connector_id(self) -> str:
        return self._connector_id

    def metadata(self) -> ConnectorMetadata:
        return self._metadata

    def configuration(self) -> ConnectorConfiguration:
        return self._config

    def health(self) -> ConnectorHealth:
        if not self._enabled:
            return ConnectorHealth(
                connector_id=self._connector_id,
                status="unavailable",
                message="Fake connector is disabled.",
                imported_document_count=self._imported_count,
                pending_changes=self._pending_changes,
                last_synchronized_at=self._last_synchronized_at,
                errors=tuple(self._last_errors),
            )
        if not self._healthy:
            return ConnectorHealth(
                connector_id=self._connector_id,
                status="unhealthy",
                message="Fake connector is marked unhealthy.",
                imported_document_count=self._imported_count,
                pending_changes=self._pending_changes,
                last_synchronized_at=self._last_synchronized_at,
                errors=tuple(self._last_errors) or ("marked unhealthy",),
            )
        return ConnectorHealth(
            connector_id=self._connector_id,
            status="healthy",
            message="Fake connector is ready.",
            imported_document_count=self._imported_count,
            pending_changes=self._pending_changes,
            last_synchronized_at=self._last_synchronized_at,
            errors=tuple(self._last_errors),
        )

    def sync(self, context: ConnectorExecutionContext) -> ConnectorResult:
        if context.connector_id != self._connector_id:
            return ConnectorResult.failure_result(
                connector_id=self._connector_id,
                sync_mode=context.sync_mode,
                error_code="invalid_context",
                error_message="Execution context connector_id does not match this connector.",
            )
        if not self._enabled:
            return ConnectorResult.failure_result(
                connector_id=self._connector_id,
                sync_mode=context.sync_mode,
                error_code="unavailable",
                error_message="Fake connector is disabled.",
            )
        if not self._healthy:
            self._last_errors = ["sync refused: unhealthy"]
            return ConnectorResult.failure_result(
                connector_id=self._connector_id,
                sync_mode=context.sync_mode,
                error_code="unhealthy",
                error_message="Fake connector is marked unhealthy.",
                pending_changes=self._pending_changes,
            )

        items: list[NormalizedImportItem] = []
        imported = 0
        for name, body in self._seed_items:
            external_id = f"fake:{name}"
            item = NormalizedImportItem(
                name=name,
                mime_type="text/plain",
                content=body.encode("utf-8"),
                metadata=NormalizedSourceMetadata(
                    connector_id=self._connector_id,
                    external_id=external_id,
                    workspace_id=context.workspace_id,
                    source="fake://local",
                    owner="fake",
                    tags=("fake",),
                ),
                change_kind="upsert",
            )
            self._document_import.import_item(item)
            items.append(item)
            imported += 1

        self._imported_count += imported
        self._pending_changes = 0
        self._last_errors = []
        self._last_synchronized_at = datetime.now(tz=UTC)
        self._cursor = f"fake-cursor-{context.sync_mode}"
        self._config = ConnectorConfiguration(
            connector_id=self._connector_id,
            enabled=self._enabled,
            auth=self._config.auth,
            sync_cursor=self._cursor,
            options=self._config.options,
        )

        return ConnectorResult.success_result(
            connector_id=self._connector_id,
            sync_mode=context.sync_mode,
            imported_count=imported,
            pending_changes=0,
            cursor=self._cursor,
            items=tuple(items),
        )


def register_fake_connector(
    registry: object,
    *,
    document_import: InMemoryDocumentImportPort | None = None,
    enabled: bool = True,
    healthy: bool = True,
) -> FakeConnector:
    """Register a FakeConnector on a ConnectorRegistry-like object."""
    connector = FakeConnector(
        document_import=document_import,
        enabled=enabled,
        healthy=healthy,
    )
    registry.register(connector)  # type: ignore[attr-defined]
    return connector
