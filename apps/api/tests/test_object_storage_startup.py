"""Object storage startup selection has no silent in-memory fallback."""

from __future__ import annotations

import logging
from unittest.mock import patch

import pytest
from api.lifespan import startup_object_storage
from documents.infrastructure.storage import InMemoryObjectStorage, MinioObjectStorage
from memovi_config.exceptions import ConfigurationError
from memovi_config.settings import validate_configuration


def _settings(**overrides: str):
    env = {
        "MEMOVI_ENV": "local",
        "INTELLIGENCE_PROVIDER": "fake",
        "SEARCH_EMBEDDING_PROVIDER": "fake",
        "POSTGRES_USER": "memovi_app",
        "POSTGRES_PASSWORD": "secret-db-password",
        "POSTGRES_HOST": "127.0.0.1",
        "POSTGRES_PORT": "5432",
        "POSTGRES_DB": "memovi",
        "MINIO_SERVER_URL": "http://127.0.0.1:9000",
        "MINIO_ROOT_USER": "minio_user",
        "MINIO_ROOT_PASSWORD": "secret-minio-password",
        "MINIO_BUCKET": "memovi-documents",
        "MINIO_REGION_NAME": "us-east-1",
    }
    env.update(overrides)
    return validate_configuration(env)


def test_explicit_memory_backend_logs_development_only(caplog: pytest.LogCaptureFixture) -> None:
    settings = _settings(MEMOVI_OBJECT_STORAGE="memory")
    with caplog.at_level(logging.INFO, logger="memovi.api"):
        storage = startup_object_storage(settings)
    assert isinstance(storage, InMemoryObjectStorage)
    assert "Using InMemoryObjectStorage (development only)" in caplog.text


def test_minio_backend_logs_active_adapter(caplog: pytest.LogCaptureFixture) -> None:
    settings = _settings()
    sentinel = object()
    with (
        patch.object(MinioObjectStorage, "from_env", return_value=sentinel),
        caplog.at_level(logging.INFO, logger="memovi.api"),
    ):
        storage = startup_object_storage(settings)
    assert storage is sentinel
    assert "Using MinioObjectStorage" in caplog.text


def test_minio_unavailable_fails_startup_with_fix_guidance() -> None:
    settings = _settings()
    with (
        patch.object(
            MinioObjectStorage,
            "from_env",
            side_effect=ConnectionError("timed out"),
        ),
        pytest.raises(ConfigurationError, match="Persistent object storage is required"),
    ):
        startup_object_storage(settings)
