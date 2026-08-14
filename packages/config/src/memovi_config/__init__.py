"""Typed configuration and environment loading for Memovi."""

from memovi_config.exceptions import ConfigurationError
from memovi_config.secrets import SecretValue
from memovi_config.settings import Settings, load_settings, validate_configuration
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

__all__ = [
    "ApiSettings",
    "AuthSettings",
    "CapabilitiesSettings",
    "ConfigurationError",
    "ConnectorsSettings",
    "DatabaseSettings",
    "DesktopSettings",
    "EmbeddingsSettings",
    "ModelsSettings",
    "ObjectStorageBackend",
    "ObservabilitySettings",
    "SearchSettings",
    "SecretValue",
    "Settings",
    "StorageSettings",
    "load_settings",
    "validate_configuration",
]
