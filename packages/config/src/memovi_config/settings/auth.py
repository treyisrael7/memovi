"""Authentication process settings."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from memovi_config.env import Environ
from memovi_config.exceptions import ConfigurationError

DEFAULT_SESSION_COOKIE_NAME = "memovi_session"
DEFAULT_SESSION_TTL_DAYS = 30


@dataclass(frozen=True, slots=True)
class AuthSettings:
    """Authentication-related process settings.

    Auth API and session commands read these values as the single source of
    session cookie name and TTL configuration.
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

    @property
    def session_ttl(self) -> timedelta:
        return timedelta(days=self.session_ttl_days)

    @classmethod
    def from_environ(cls, environ: Environ) -> AuthSettings:
        del environ  # Reserved for future auth env overrides.
        return cls()
