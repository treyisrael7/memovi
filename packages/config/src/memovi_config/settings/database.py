"""Database process settings."""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse, urlunparse

from memovi_config.env import (
    Environ,
    get_int,
    get_secret,
    get_str,
    require_database_url,
)
from memovi_config.exceptions import ConfigurationError
from memovi_config.secrets import SecretValue

DEFAULT_POSTGRES_USER = "memovi_app"
DEFAULT_POSTGRES_PASSWORD = "memovi_local_pg_9f4c8e2d7a6b41c3"
DEFAULT_POSTGRES_HOST = "127.0.0.1"
DEFAULT_POSTGRES_PORT = 5432
DEFAULT_POSTGRES_DB = "memovi"


@dataclass(frozen=True, slots=True)
class DatabaseSettings:
    """Typed database connection settings.

    Prefer ``DATABASE_URL`` when set. Otherwise compose a PostgreSQL URL from
    ``POSTGRES_*`` variables (matching historical local defaults).
    """

    url: str
    user: str | None = None
    password: SecretValue | None = None
    host: str | None = None
    port: int | None = None
    database: str | None = None
    from_explicit_url: bool = False

    def __post_init__(self) -> None:
        require_database_url("DATABASE_URL" if self.from_explicit_url else "database URL", self.url)

    @property
    def safe_url(self) -> str:
        """Return the connection URL with password redacted for diagnostics."""
        return redact_database_url(self.url)

    def __repr__(self) -> str:
        return (
            "DatabaseSettings("
            f"url={self.safe_url!r}, "
            f"user={self.user!r}, "
            f"password={'SecretValue(***)' if self.password else None}, "
            f"host={self.host!r}, "
            f"port={self.port!r}, "
            f"database={self.database!r}, "
            f"from_explicit_url={self.from_explicit_url!r})"
        )

    @classmethod
    def from_environ(cls, environ: Environ) -> DatabaseSettings:
        explicit = get_str(environ, "DATABASE_URL", default=None)
        if explicit is not None:
            return cls(url=explicit, from_explicit_url=True)

        user = get_str(environ, "POSTGRES_USER", default=DEFAULT_POSTGRES_USER) or (
            DEFAULT_POSTGRES_USER
        )
        password = get_secret(
            environ,
            "POSTGRES_PASSWORD",
            default=DEFAULT_POSTGRES_PASSWORD,
        )
        if password is None:
            raise ConfigurationError("POSTGRES_PASSWORD is required.")
        host = get_str(environ, "POSTGRES_HOST", default=DEFAULT_POSTGRES_HOST) or (
            DEFAULT_POSTGRES_HOST
        )
        port = get_int(
            environ,
            "POSTGRES_PORT",
            default=DEFAULT_POSTGRES_PORT,
            minimum=1,
            maximum=65535,
        )
        database = get_str(environ, "POSTGRES_DB", default=DEFAULT_POSTGRES_DB) or (
            DEFAULT_POSTGRES_DB
        )
        # Preserve historical URL construction (password is not percent-encoded).
        url = (
            f"postgresql+psycopg://{user}:{password.get_secret_value()}"
            f"@{host}:{port}/{database}"
        )
        return cls(
            url=url,
            user=user,
            password=password,
            host=host,
            port=port,
            database=database,
            from_explicit_url=False,
        )


def redact_database_url(url: str) -> str:
    """Redact userinfo password from a database URL for safe display."""
    parsed = urlparse(url)
    if not parsed.password and "@" not in (parsed.netloc or ""):
        return url
    hostname = parsed.hostname or ""
    port = f":{parsed.port}" if parsed.port else ""
    username = parsed.username or ""
    netloc = f"{username}:***@{hostname}{port}" if username else f"***@{hostname}{port}"
    return urlunparse(
        (parsed.scheme, netloc, parsed.path, parsed.params, parsed.query, parsed.fragment)
    )
