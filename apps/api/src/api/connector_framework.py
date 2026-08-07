"""Composition-root wiring for the Connector Framework."""

from __future__ import annotations

from fastapi import FastAPI
from memovi_connectors import ConnectorRegistry, ConnectorScheduler


def configure_connector_framework(app: FastAPI) -> ConnectorRegistry:
    """Attach an empty connector registry and scheduler foundation to the app.

    Concrete provider connectors register explicitly here in future milestones.
    The Fake connector is intentionally not registered in production wiring.
    """
    registry = ConnectorRegistry()
    scheduler = ConnectorScheduler(registry)
    app.state.connector_registry = registry
    app.state.connector_scheduler = scheduler
    return registry
