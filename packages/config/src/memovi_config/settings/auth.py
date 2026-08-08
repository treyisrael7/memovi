"""Authentication process settings."""

from __future__ import annotations

from dataclasses import dataclass

from memovi_config.env import Environ
from memovi_config.exceptions import ConfigurationError

# Mirrors packages/auth until auth reads these via memovi_config.
DEFAULT_SESSION_COOKIE_NAME = "memovi_session"
DEFAULT_SESSION_TTL_DAYS = 30


@dataclass(frozen=True, slots=True)
class AuthSettings:
    """Authentication-related process settings.

    Session cookie name and TTL currently remain module constants in the auth
    package with these same defaults. This typed object is part of startup
    validation so auth configuration is covered by the central Settings aggregate.
    """

    session_cookie_name: str = DEFAULT_SESSION_COOKIE_NAME
    session_ttl_days: int = DEFAULT_SESSION_TTL_DAYS

    def __post_init__(self) -> None:
        name = self.session_cookie_name.strip()
        if not name:
            raise ConfigurationError("session_cookie_name cannot be blank.")
        object.__setattr__(self, "session_cookie_name", name)
        if self.session_ttl_days < 1:
            raise ConfigurationError("session_ttl_days must be at least 1.")

    @classmethod
    def from_environ(cls, environ: Environ) -> AuthSettings:
        del environ  # Reserved for future auth env overrides.
        return cls()
