"""Unit tests for the Connector Framework foundation."""

from __future__ import annotations

import pytest
from memovi_shared import WorkspaceId

from memovi_connectors import (
    AuthCredentialRef,
    ConnectorConfiguration,
    ConnectorExecutionContext,
    ConnectorHealth,
    ConnectorMetadata,
    ConnectorRegistry,
    ConnectorResult,
    ConnectorScheduler,
    ConnectorScheduleSpec,
    FakeConnector,
    InMemoryDocumentImportPort,
    InvalidConnectorError,
    NormalizedImportItem,
    NormalizedSourceMetadata,
    UnknownConnectorError,
    register_fake_connector,
)


def test_registry_register_list_and_lookup() -> None:
    registry = ConnectorRegistry()
    connector = FakeConnector()
    registry.register(connector)

    assert registry.list_connectors() == ("fake",)
    assert registry.contains("fake")
    assert registry.get("fake") is connector
    assert registry.list_metadata()[0].display_name == "Fake Connector"


def test_registry_rejects_duplicates_and_unknown() -> None:
    registry = ConnectorRegistry()
    register_fake_connector(registry)
    with pytest.raises(InvalidConnectorError, match="already registered"):
        register_fake_connector(registry)
    with pytest.raises(UnknownConnectorError):
        registry.get("github")


def test_auth_credential_ref_rejects_secrets_without_ref() -> None:
    with pytest.raises(InvalidConnectorError, match="secret_env or secret_ref"):
        AuthCredentialRef(method="api_key")


def test_configuration_isolates_credentials() -> None:
    config = ConnectorConfiguration(
        connector_id="github",
        auth=AuthCredentialRef(method="personal_access_token", secret_env="MEMOVI_GITHUB_TOKEN"),
        options={"org": "memovi"},
    )
    assert config.auth.secret_env == "MEMOVI_GITHUB_TOKEN"
    assert "token" not in config.options


def test_fake_connector_sync_imports_through_document_port() -> None:
    document_import = InMemoryDocumentImportPort()
    connector = FakeConnector(document_import=document_import)
    context = ConnectorExecutionContext.create(
        workspace_id=WorkspaceId.default(),
        connector_id="fake",
        sync_mode="initial",
    )

    result = connector.sync(context)

    assert result.success is True
    assert result.imported_count == 1
    assert len(document_import.imported) == 1
    item = document_import.imported[0]
    assert item.metadata.connector_id == "fake"
    assert item.metadata.external_id == "fake:readme.txt"
    assert item.metadata.workspace_id == WorkspaceId.default()
    assert item.content == b"Fake connector content."
    health = connector.health()
    assert health.is_healthy
    assert health.imported_document_count == 1
    assert health.pending_changes == 0
    assert health.last_synchronized_at is not None


def test_fake_connector_reports_unhealthy_sync_failure() -> None:
    connector = FakeConnector(healthy=False)
    result = connector.sync(
        ConnectorExecutionContext.create(
            workspace_id=WorkspaceId.default(),
            connector_id="fake",
            sync_mode="incremental",
        ),
    )
    assert result.success is False
    assert result.error_code == "unhealthy"
    assert connector.health().status == "unhealthy"


def test_scheduler_registers_specs_without_running_them() -> None:
    registry = ConnectorRegistry()
    register_fake_connector(registry)
    scheduler = ConnectorScheduler(registry)
    workspace_id = WorkspaceId.default()

    scheduler.register_schedule(
        ConnectorScheduleSpec(
            connector_id="fake",
            workspace_id=workspace_id,
            sync_mode="incremental",
            interval_seconds=3600,
        ),
    )

    specs = scheduler.list_schedules()
    assert len(specs) == 1
    assert specs[0].interval_seconds == 3600
    assert scheduler.get_schedule(connector_id="fake", workspace_id=workspace_id) is not None


def test_scheduler_run_now_executes_sync() -> None:
    registry = ConnectorRegistry()
    connector = register_fake_connector(registry)
    scheduler = ConnectorScheduler(registry)

    result = scheduler.run_now(
        connector_id="fake",
        context=ConnectorExecutionContext.create(
            workspace_id=WorkspaceId.default(),
            connector_id="fake",
            sync_mode="initial",
        ),
    )

    assert result.success is True
    assert len(connector.document_import.imported) == 1


def test_scheduler_rejects_unknown_connector_schedule() -> None:
    scheduler = ConnectorScheduler(ConnectorRegistry())
    with pytest.raises(UnknownConnectorError):
        scheduler.register_schedule(
            ConnectorScheduleSpec(
                connector_id="github",
                workspace_id=WorkspaceId.default(),
            ),
        )


def test_normalized_import_item_and_health_invariants() -> None:
    metadata = NormalizedSourceMetadata(
        connector_id="fake",
        external_id="ext-1",
        workspace_id=WorkspaceId.default(),
        source="fake://",
        tags=("a", "b"),
    )
    item = NormalizedImportItem(
        name="note.md",
        mime_type="text/markdown",
        content=b"# hi",
        metadata=metadata,
    )
    assert item.change_kind == "upsert"

    health = ConnectorHealth(
        connector_id="fake",
        status="degraded",
        imported_document_count=3,
        pending_changes=2,
        errors=("rate limited",),
    )
    assert health.status == "degraded"
    assert health.errors == ("rate limited",)

    with pytest.raises(InvalidConnectorError):
        ConnectorResult.failure_result(
            connector_id="fake",
            sync_mode="initial",
            error_code="",
            error_message="",
        )


def test_registry_health_all() -> None:
    registry = ConnectorRegistry()
    register_fake_connector(registry)
    snapshots = registry.health_all()
    assert len(snapshots) == 1
    assert snapshots[0].connector_id == "fake"


def test_metadata_rejects_unknown_category() -> None:
    with pytest.raises(InvalidConnectorError, match="source_category"):
        ConnectorMetadata(
            connector_id="x",
            display_name="X",
            description="",
            source_category="not-a-category",
        )
