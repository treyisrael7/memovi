"""Connector Framework domain exceptions."""


class ConnectorsDomainError(Exception):
    """Base error for the Connector Framework."""


class InvalidConnectorError(ConnectorsDomainError):
    """Raised when connector metadata, configuration, or inputs are invalid."""


class UnknownConnectorError(ConnectorsDomainError):
    """Raised when a connector id is not registered."""


class ConnectorSyncError(ConnectorsDomainError):
    """Raised when a connector sync fails in a non-normalized way.

    Prefer returning a failed :class:`ConnectorResult` for expected sync
    outcomes. Use this for programming / contract violations.
    """

    def __init__(self, message: str, *, code: str = "connector_error") -> None:
        super().__init__(message)
        self.code = code
