"""API process settings."""

from __future__ import annotations

from dataclasses import dataclass

from memovi_config.env import Environ, get_str
from memovi_config.exceptions import ConfigurationError


@dataclass(frozen=True, slots=True)
class ApiSettings:
    """Settings for the API composition root and readiness metadata."""

    environment: str = "local"

    def __post_init__(self) -> None:
        environment = self.environment.strip()
        if not environment:
            raise ConfigurationError("MEMOVI_ENV cannot be blank.")
        object.__setattr__(self, "environment", environment)

    @classmethod
    def from_environ(cls, environ: Environ) -> ApiSettings:
        return cls(
            environment=get_str(environ, "MEMOVI_ENV", default="local") or "local",
        )
