"""Aggregate typed application settings."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass

from memovi_config.env import Environ
from memovi_config.exceptions import ConfigurationError
from memovi_config.settings.api import ApiSettings
from memovi_config.settings.auth import AuthSettings
from memovi_config.settings.capabilities import CapabilitiesSettings
from memovi_config.settings.connectors import ConnectorsSettings
from memovi_config.settings.database import DatabaseSettings
from memovi_config.settings.desktop import DesktopSettings
from memovi_config.settings.embeddings import EmbeddingsSettings
from memovi_config.settings.models import ModelsSettings
from memovi_config.settings.observability import ObservabilitySettings
from memovi_config.settings.search import SearchSettings
from memovi_config.settings.storage import ObjectStorageBackend, StorageSettings


@dataclass(frozen=True, slots=True)
class Settings:
    """Authoritative typed configuration for the Memovi platform process."""

    api: ApiSettings
    database: DatabaseSettings
    auth: AuthSettings
    search: SearchSettings
    embeddings: EmbeddingsSettings
    models: ModelsSettings
    storage: StorageSettings
    capabilities: CapabilitiesSettings
    connectors: ConnectorsSettings
    observability: ObservabilitySettings
    desktop: DesktopSettings

    @classmethod
    def from_environ(cls, environ: Environ) -> Settings:
        """Load and validate all configuration domains from ``environ``."""
        models = ModelsSettings.from_environ(environ)
        models.ensure_provider_secrets()
        settings = cls(
            api=ApiSettings.from_environ(environ),
            database=DatabaseSettings.from_environ(environ),
            auth=AuthSettings.from_environ(environ),
            search=SearchSettings.from_environ(environ),
            embeddings=EmbeddingsSettings.from_environ(environ),
            models=models,
            storage=StorageSettings.from_environ(environ),
            capabilities=CapabilitiesSettings.from_environ(environ),
            connectors=ConnectorsSettings.from_environ(environ),
            observability=ObservabilitySettings.from_environ(environ),
            desktop=DesktopSettings.from_environ(environ),
        )
        settings.ensure_object_storage_policy()
        return settings

    def ensure_object_storage_policy(self) -> None:
        """Reject in-memory object storage outside explicit development environments."""
        if self.storage.backend != ObjectStorageBackend.MEMORY:
            return
        if self.api.allows_in_memory_object_storage():
            return
        raise ConfigurationError(
            "MEMOVI_OBJECT_STORAGE=memory is only allowed in development "
            f"(MEMOVI_ENV={self.api.environment}). Use MinIO in production: "
            "start object storage and leave MEMOVI_OBJECT_STORAGE unset "
            "(defaults to minio), or set MEMOVI_OBJECT_STORAGE=minio.",
        )


def load_settings(environ: Mapping[str, str] | None = None) -> Settings:
    """Load typed settings from the process environment (or a test mapping)."""
    env: Environ = environ if environ is not None else os.environ
    return Settings.from_environ(env)


def validate_configuration(environ: Mapping[str, str] | None = None) -> Settings:
    """Fail fast when required environment configuration is missing or invalid.

    Returns the validated ``Settings`` aggregate. Raises ``ConfigurationError``
    (a ``ValueError``) on the first invalid domain. Secret values never appear
    in exception messages.
    """
    return load_settings(environ)
