"""Configuration validation tests for memovi_config."""

from __future__ import annotations

from pathlib import Path

import pytest
from memovi_config import (
    ConfigurationError,
    SecretValue,
    Settings,
    load_settings,
    validate_configuration,
)
from memovi_config.settings.database import DatabaseSettings, redact_database_url
from memovi_config.settings.embeddings import EMBEDDING_VECTOR_DIMENSIONS, EmbeddingsSettings
from memovi_config.settings.models import ModelsSettings
from memovi_config.settings.storage import StorageSettings


def _base_environ(**overrides: str) -> dict[str, str]:
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
    return env


def test_valid_configuration_loads_all_domains() -> None:
    settings = validate_configuration(_base_environ())
    assert isinstance(settings, Settings)
    assert settings.api.environment == "local"
    assert settings.embeddings.provider == "fake"
    assert settings.models.provider == "fake"
    assert settings.database.host == "127.0.0.1"
    assert settings.storage.bucket_name == "memovi-documents"
    assert settings.storage.backend == "minio"
    assert "secret-db-password" in settings.database.url
    assert "secret-db-password" not in settings.database.safe_url
    assert "secret-db-password" not in repr(settings.database)


def test_explicit_in_memory_object_storage_allowed_in_test_env() -> None:
    settings = validate_configuration(
        _base_environ(MEMOVI_OBJECT_STORAGE="memory", MEMOVI_ENV="test"),
    )
    assert settings.storage.backend == "memory"


def test_missing_required_openai_key_for_embeddings() -> None:
    with pytest.raises(ConfigurationError, match="OPENAI_API_KEY"):
        EmbeddingsSettings.from_environ(
            _base_environ(SEARCH_EMBEDDING_PROVIDER="openai"),
        )


def test_missing_required_openai_key_for_models_at_startup() -> None:
    with pytest.raises(ConfigurationError, match="OPENAI_API_KEY"):
        validate_configuration(_base_environ(INTELLIGENCE_PROVIDER="openai"))


def test_models_from_environ_allows_openai_without_key() -> None:
    models = ModelsSettings.from_environ(_base_environ(INTELLIGENCE_PROVIDER="openai"))
    assert models.provider == "openai"
    assert models.model == "gpt-4o-mini"


def test_fake_reasoning_provider_accepted() -> None:
    settings = validate_configuration(_base_environ(INTELLIGENCE_PROVIDER="fake"))
    assert settings.models.provider == "fake"


def test_openai_reasoning_provider_accepted_with_api_key() -> None:
    settings = validate_configuration(
        _base_environ(INTELLIGENCE_PROVIDER="openai", OPENAI_API_KEY="sk-test"),
    )
    assert settings.models.provider == "openai"
    assert settings.models.openai_api_key is not None


@pytest.mark.parametrize(
    "provider",
    ("anthropic", "ollama", "gemini", "foo"),
)
def test_unsupported_reasoning_provider_rejected_at_configuration(provider: str) -> None:
    with pytest.raises(
        ConfigurationError,
        match=f"Unsupported reasoning provider '{provider}'. V1 supports: fake, openai.",
    ):
        validate_configuration(_base_environ(INTELLIGENCE_PROVIDER=provider))


def test_blank_reasoning_provider_rejected() -> None:
    with pytest.raises(ConfigurationError, match="INTELLIGENCE_PROVIDER cannot be blank"):
        ModelsSettings(provider="")


def test_ollama_embedding_provider_remains_valid() -> None:
    settings = validate_configuration(
        _base_environ(SEARCH_EMBEDDING_PROVIDER="ollama", INTELLIGENCE_PROVIDER="fake"),
    )
    assert settings.embeddings.provider == "ollama"
    assert settings.models.provider == "fake"


def test_invalid_embedding_provider_enum() -> None:
    with pytest.raises(ConfigurationError, match="Unsupported embedding provider"):
        EmbeddingsSettings.from_environ(
            _base_environ(SEARCH_EMBEDDING_PROVIDER="not-a-provider"),
        )


def test_invalid_log_level_enum() -> None:
    with pytest.raises(ConfigurationError, match="MEMOVI_LOG_LEVEL"):
        load_settings(_base_environ(MEMOVI_LOG_LEVEL="verbose"))


def test_invalid_database_url() -> None:
    with pytest.raises(ConfigurationError, match="postgresql or sqlite"):
        DatabaseSettings.from_environ({"DATABASE_URL": "not-a-url"})


def test_invalid_minio_url() -> None:
    with pytest.raises(ConfigurationError, match="http\\(s\\) URL"):
        StorageSettings.from_environ(
            _base_environ(MINIO_SERVER_URL="ftp://127.0.0.1:9000"),
        )


def test_explicit_in_memory_object_storage_allowed_in_local() -> None:
    settings = validate_configuration(
        _base_environ(MEMOVI_OBJECT_STORAGE="memory", MEMOVI_ENV="local"),
    )
    assert settings.storage.backend == "memory"


def test_in_memory_object_storage_rejected_in_production() -> None:
    with pytest.raises(ConfigurationError, match="only allowed in development"):
        validate_configuration(
            _base_environ(MEMOVI_OBJECT_STORAGE="memory", MEMOVI_ENV="production"),
        )


def test_invalid_object_storage_backend() -> None:
    with pytest.raises(ConfigurationError, match="Unsupported object storage backend"):
        StorageSettings.from_environ(_base_environ(MEMOVI_OBJECT_STORAGE="disk"))


def test_invalid_numeric_port() -> None:
    with pytest.raises(ConfigurationError, match="integer"):
        DatabaseSettings.from_environ(_base_environ(POSTGRES_PORT="abc"))


def test_invalid_numeric_timeout() -> None:
    with pytest.raises(ConfigurationError, match="number"):
        EmbeddingsSettings.from_environ(
            _base_environ(SEARCH_EMBEDDING_TIMEOUT_SECONDS="fast"),
        )


def test_invalid_embedding_dimensions() -> None:
    with pytest.raises(ConfigurationError, match="pgvector"):
        EmbeddingsSettings.from_environ(
            _base_environ(
                SEARCH_EMBEDDING_DIMENSIONS=str(EMBEDDING_VECTOR_DIMENSIONS + 1),
            ),
        )


def test_invalid_capability_root_missing(tmp_path: Path) -> None:
    missing = tmp_path / "does-not-exist"
    with pytest.raises(ConfigurationError, match="does not exist"):
        load_settings(
            _base_environ(MEMOVI_FILESYSTEM_ROOTS=str(missing)),
        )


def test_valid_capability_roots(tmp_path: Path) -> None:
    root = tmp_path / "workspace"
    root.mkdir()
    settings = load_settings(_base_environ(MEMOVI_FILESYSTEM_ROOTS=str(root)))
    assert settings.capabilities.filesystem_roots == (root.resolve(),)


def test_secret_value_never_reveals_contents() -> None:
    secret = SecretValue("super-secret-value")
    assert secret.get_secret_value() == "super-secret-value"
    assert "super-secret-value" not in str(secret)
    assert "super-secret-value" not in repr(secret)
    assert str(secret) == "***"


def test_redact_database_url_hides_password() -> None:
    url = "postgresql+psycopg://user:hunter2@127.0.0.1:5432/memovi"
    redacted = redact_database_url(url)
    assert "hunter2" not in redacted
    assert "user:***@" in redacted


def test_explicit_database_url() -> None:
    settings = DatabaseSettings.from_environ(
        {"DATABASE_URL": "postgresql+psycopg://u:p@localhost:5432/db"},
    )
    assert settings.from_explicit_url is True
    assert settings.url.endswith("/db")
