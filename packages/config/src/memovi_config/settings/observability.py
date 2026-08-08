"""Observability process settings."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from memovi_config.env import Environ, get_str
from memovi_config.exceptions import ConfigurationError


class LogLevelName(StrEnum):
    """Supported log level names for ``MEMOVI_LOG_LEVEL``."""

    CRITICAL = "critical"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    DEBUG = "debug"


@dataclass(frozen=True, slots=True)
class ObservabilitySettings:
    """Logging and environment labeling for observability."""

    environment: str = "local"
    log_level: str = LogLevelName.INFO.value

    def __post_init__(self) -> None:
        environment = self.environment.strip()
        if not environment:
            raise ConfigurationError("MEMOVI_ENV cannot be blank.")
        object.__setattr__(self, "environment", environment)

        level = self.log_level.strip().lower()
        try:
            resolved = LogLevelName(level)
        except ValueError as exc:
            supported = ", ".join(item.value for item in LogLevelName)
            raise ConfigurationError(
                f"Unsupported MEMOVI_LOG_LEVEL '{level}'. Supported: {supported}.",
            ) from exc
        object.__setattr__(self, "log_level", resolved.value)

    @classmethod
    def from_environ(cls, environ: Environ) -> ObservabilitySettings:
        return cls(
            environment=get_str(environ, "MEMOVI_ENV", default="local") or "local",
            log_level=get_str(environ, "MEMOVI_LOG_LEVEL", default="info") or "info",
        )
