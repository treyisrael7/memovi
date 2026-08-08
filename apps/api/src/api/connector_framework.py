"""Composition-root wiring for the Connector Framework."""

from __future__ import annotations

from fastapi import FastAPI
from memovi_connectors import ConnectorRegistry, ConnectorScheduler
from memovi_connectors.infrastructure.filesystem_connector import register_filesystem_connector


def configure_connector_framework(app: FastAPI) -> ConnectorRegistry:
    """Attach connector registry, scheduler, and production filesystem connector.

    Request-scoped ``DocumentImportPort`` and folder repository bindings are
    applied during filesystem sync via ``FilesystemConnector.configure_runtime``.
    """
    registry = ConnectorRegistry()
    scheduler = ConnectorScheduler(registry)
    filesystem = register_filesystem_connector(registry)
    app.state.connector_registry = registry
    app.state.connector_scheduler = scheduler
    app.state.filesystem_connector = filesystem
    return registry
