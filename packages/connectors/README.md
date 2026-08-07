# Memovi Connectors

Connector Framework for importing and synchronizing knowledge from external
systems into Memovi's Documents → Memory → Search → Intelligence pipeline.

## Ownership

This package owns:

* Connector contracts and registry
* Authentication references (not secret storage)
* Synchronization and change detection contracts
* Metadata normalization
* Connector health
* Scheduler foundation (no timed runs yet)

It does **not** own document storage, processing, knowledge extraction, search
indexing, or provider-specific product logic.

## Usage

```python
from memovi_connectors import (
    ConnectorRegistry,
    ConnectorScheduler,
    FakeConnector,
    ConnectorExecutionContext,
)
from memovi_shared import WorkspaceId

registry = ConnectorRegistry()
connector = FakeConnector()
registry.register(connector)

scheduler = ConnectorScheduler(registry)
result = scheduler.run_now(
    connector_id=connector.connector_id(),
    context=ConnectorExecutionContext.create(
        workspace_id=WorkspaceId.default(),
        connector_id=connector.connector_id(),
        sync_mode="initial",
    ),
)
```

See [`docs/architecture/CONNECTOR_FRAMEWORK.md`](../../docs/architecture/CONNECTOR_FRAMEWORK.md).
