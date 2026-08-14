"""Object storage startup selection has no silent in-memory fallback."""

from __future__ import annotations

import logging
from unittest.mock import patch

import pytest
from api.document_processing import (
    MEMORY_STORAGE_LABEL,
    MINIO_STORAGE_LABEL,
    configure_document_processing,
)
from api.health import _check_object_storage
from api.lifespan import startup_object_storage
from documents.infrastructure.events.noop_event_publisher import NoOpEventPublisher
from documents.infrastructure.queue import NoOpProcessingJobQueue
from documents.infrastructure.storage import InMemoryObjectStorage, MinioObjectStorage
from fastapi import FastAPI
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


def test_explicit_memory_backend_logs_development_only(
    caplog: pytest.LogCaptureFixture,
) -> None:
    settings = _settings(MEMOVI_OBJECT_STORAGE="memory")
    with caplog.at_level(logging.INFO, logger="memovi.api"):
        storage = startup_object_storage(settings)
    assert isinstance(storage, InMemoryObjectStorage)
    assert MEMORY_STORAGE_LABEL in caplog.text


def test_minio_backend_logs_active_adapter(caplog: pytest.LogCaptureFixture) -> None:
    settings = _settings()
    sentinel = object()
    with (
        patch.object(MinioObjectStorage, "from_env", return_value=sentinel),
        caplog.at_level(logging.INFO, logger="memovi.api"),
    ):
        storage = startup_object_storage(settings)
    assert storage is sentinel
    assert MINIO_STORAGE_LABEL in caplog.text


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


def test_production_unavailable_minio_does_not_construct_memory_storage() -> None:
    settings = _settings(MEMOVI_ENV="production")
    with (
        patch(
            "api.lifespan.InMemoryObjectStorage",
            side_effect=AssertionError("in-memory fallback is forbidden"),
        ),
        patch.object(
            MinioObjectStorage,
            "from_env",
            side_effect=OSError("connection refused"),
        ),
        pytest.raises(ConfigurationError, match="Persistent object storage is required"),
    ):
        startup_object_storage(settings)


def test_production_rejects_memory_before_storage_is_wired() -> None:
    with pytest.raises(ConfigurationError, match="only allowed in development"):
        _settings(MEMOVI_OBJECT_STORAGE="memory", MEMOVI_ENV="production")


def test_configure_document_processing_uses_explicit_storage_only() -> None:
    app = FastAPI()
    storage = InMemoryObjectStorage()
    configure_document_processing(
        app,
        session_factory=lambda: None,  # type: ignore[arg-type,return-value]
        queue=NoOpProcessingJobQueue(),
        object_storage=storage,
        storage_backend="memory",
        event_publisher=NoOpEventPublisher(),
    )
    assert app.state.object_storage is storage
    assert app.state.object_storage_backend == "memory"
    assert app.state.object_storage_label == MEMORY_STORAGE_LABEL
    assert not isinstance(app.state.object_storage, MinioObjectStorage)


def test_readiness_describes_explicit_memory_backend() -> None:
    check = _check_object_storage(
        storage=InMemoryObjectStorage(),
        backend="memory",
    )
    assert check.status == "up"
    assert check.detail == MEMORY_STORAGE_LABEL


def test_readiness_minio_down_has_operator_guidance_not_traceback() -> None:
    class Down:
        def check_available(self) -> None:
            raise ConnectionError("timed out\nTraceback (most recent call last):")

    check = _check_object_storage(storage=Down(), backend="minio")
    assert check.status == "down"
    assert check.detail is not None
    assert "MinIO" in check.detail
    assert "Traceback" not in check.detail
    assert "timed out" not in check.detail
