from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType

from memovi_connectors.domain.exceptions import InvalidConnectorError

_AUTH_METHODS = frozenset(
    {
        "none",
        "oauth",
        "api_key",
        "personal_access_token",
        "service_account",
    },
)


@dataclass(frozen=True, slots=True)
class AuthCredentialRef:
    """Reference to connector credentials without embedding secret values.

    Credentials stay in environment variables or a secret store. Connector
    implementations resolve values through composition-root wiring, never by
    reading raw secrets from configuration objects.
    """

    method: str
    secret_env: str | None = None
    secret_ref: str | None = None
    extra: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        method = self.method.strip().lower()
        if method not in _AUTH_METHODS:
            raise InvalidConnectorError(
                f"Auth credential method must be one of: {', '.join(sorted(_AUTH_METHODS))}.",
            )
        secret_env = (
            self.secret_env.strip() if isinstance(self.secret_env, str) else self.secret_env
        )
        secret_ref = (
            self.secret_ref.strip() if isinstance(self.secret_ref, str) else self.secret_ref
        )
        if isinstance(secret_env, str) and not secret_env:
            raise InvalidConnectorError("Auth credential secret_env cannot be blank when set.")
        if isinstance(secret_ref, str) and not secret_ref:
            raise InvalidConnectorError("Auth credential secret_ref cannot be blank when set.")
        if method != "none" and secret_env is None and secret_ref is None:
            raise InvalidConnectorError(
                "Auth credential requires secret_env or secret_ref when method is not 'none'.",
            )
        if not isinstance(self.extra, Mapping):
            raise InvalidConnectorError("Auth credential extra must be a mapping.")

        object.__setattr__(self, "method", method)
        object.__setattr__(self, "secret_env", secret_env)
        object.__setattr__(self, "secret_ref", secret_ref)
        object.__setattr__(self, "extra", MappingProxyType(dict(self.extra)))


@dataclass(frozen=True, slots=True)
class ConnectorConfiguration:
    """Connector instance settings independent of UI and provider SDKs.

    Secrets must not be embedded here. Use :class:`AuthCredentialRef` to point
    at environment variables or secret-store references.
    """

    connector_id: str
    enabled: bool = True
    auth: AuthCredentialRef = field(default_factory=lambda: AuthCredentialRef(method="none"))
    sync_cursor: str | None = None
    options: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        connector_id = self.connector_id.strip().lower()
        if not connector_id:
            raise InvalidConnectorError("Connector configuration connector_id is required.")
        if not isinstance(self.auth, AuthCredentialRef):
            raise InvalidConnectorError(
                "Connector configuration auth must be an AuthCredentialRef.",
            )
        sync_cursor = (
            self.sync_cursor.strip() if isinstance(self.sync_cursor, str) else self.sync_cursor
        )
        if isinstance(sync_cursor, str) and not sync_cursor:
            raise InvalidConnectorError(
                "Connector configuration sync_cursor cannot be blank when set.",
            )
        if not isinstance(self.options, Mapping):
            raise InvalidConnectorError("Connector configuration options must be a mapping.")

        object.__setattr__(self, "connector_id", connector_id)
        object.__setattr__(self, "sync_cursor", sync_cursor)
        object.__setattr__(self, "options", MappingProxyType(dict(self.options)))
