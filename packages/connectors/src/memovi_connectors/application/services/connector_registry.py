from memovi_connectors.application.ports import Connector
from memovi_connectors.domain.exceptions import InvalidConnectorError, UnknownConnectorError
from memovi_connectors.domain.value_objects import ConnectorHealth, ConnectorMetadata


class ConnectorRegistry:
    """Registers and discovers connectors without global mutable state.

    Connectors are registered explicitly through dependency injection.
    """

    def __init__(self) -> None:
        self._connectors: dict[str, Connector] = {}

    def register(self, connector: Connector) -> None:
        connector_id = connector.connector_id().strip().lower()
        if not connector_id:
            raise InvalidConnectorError("Cannot register a connector with a blank id.")
        metadata = connector.metadata()
        if metadata.connector_id != connector_id:
            raise InvalidConnectorError(
                f"Connector metadata id '{metadata.connector_id}' does not match "
                f"connector id '{connector_id}'.",
            )
        configuration = connector.configuration()
        if configuration.connector_id != connector_id:
            raise InvalidConnectorError(
                f"Connector configuration id '{configuration.connector_id}' does not match "
                f"connector id '{connector_id}'.",
            )
        if connector_id in self._connectors:
            raise InvalidConnectorError(f"Connector '{connector_id}' is already registered.")
        self._connectors[connector_id] = connector

    def get(self, connector_id: str) -> Connector:
        connector = self._connectors.get(connector_id.strip().lower())
        if connector is None:
            raise UnknownConnectorError(f"Unknown connector '{connector_id}'.")
        return connector

    def list_connectors(self) -> tuple[str, ...]:
        return tuple(self._connectors.keys())

    def list_metadata(self) -> tuple[ConnectorMetadata, ...]:
        return tuple(connector.metadata() for connector in self._connectors.values())

    def health(self, connector_id: str) -> ConnectorHealth:
        return self.get(connector_id).health()

    def health_all(self) -> tuple[ConnectorHealth, ...]:
        return tuple(connector.health() for connector in self._connectors.values())

    def contains(self, connector_id: str) -> bool:
        return connector_id.strip().lower() in self._connectors
