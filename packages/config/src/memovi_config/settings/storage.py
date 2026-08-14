"""Object storage process settings."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from memovi_config.env import Environ, get_secret, get_str, require_http_url
from memovi_config.exceptions import ConfigurationError
from memovi_config.secrets import SecretValue

DEFAULT_MINIO_ENDPOINT = "http://127.0.0.1:9000"
DEFAULT_MINIO_ACCESS_KEY = "memovi_minio_admin"
DEFAULT_MINIO_SECRET_KEY = "memovi_local_minio_5c7f1e9a3b6d4a82"
DEFAULT_MINIO_BUCKET = "memovi-documents"
DEFAULT_MINIO_REGION = "us-east-1"
DEFAULT_OBJECT_STORAGE_BACKEND = "minio"


class ObjectStorageBackend(StrEnum):
    """Supported object-storage backends. ``memory`` is an explicit local opt-in."""

    MINIO = "minio"
    MEMORY = "memory"


@dataclass(frozen=True, slots=True)
class StorageSettings:
    """Typed MinIO / S3-compatible object storage settings.

    Backend selection is explicit. Connectivity for ``minio`` is checked at
    process startup; there is no silent in-memory fallback.
    """

    endpoint_url: str = DEFAULT_MINIO_ENDPOINT
    access_key: SecretValue = field(
        default_factory=lambda: SecretValue(DEFAULT_MINIO_ACCESS_KEY),
    )
    secret_key: SecretValue = field(
        default_factory=lambda: SecretValue(DEFAULT_MINIO_SECRET_KEY),
    )
    bucket_name: str = DEFAULT_MINIO_BUCKET
    region_name: str = DEFAULT_MINIO_REGION
    backend: str = DEFAULT_OBJECT_STORAGE_BACKEND

    def __post_init__(self) -> None:
        backend = self.backend.strip().lower()
        if not backend:
            raise ConfigurationError("MEMOVI_OBJECT_STORAGE cannot be blank.")
        try:
            kind = ObjectStorageBackend(backend)
        except ValueError as exc:
            supported = ", ".join(item.value for item in ObjectStorageBackend)
            raise ConfigurationError(
                f"Unsupported object storage backend '{backend}'. " f"Supported: {supported}.",
            ) from exc
        object.__setattr__(self, "backend", kind.value)

        require_http_url("MINIO_SERVER_URL", self.endpoint_url)
        if not self.access_key.get_secret_value().strip():
            raise ConfigurationError("MINIO_ROOT_USER cannot be blank.")
        if not self.secret_key.get_secret_value().strip():
            raise ConfigurationError("MINIO_ROOT_PASSWORD cannot be blank.")
        bucket = self.bucket_name.strip()
        if not bucket:
            raise ConfigurationError("MINIO_BUCKET cannot be blank.")
        object.__setattr__(self, "bucket_name", bucket)
        region = self.region_name.strip()
        if not region:
            raise ConfigurationError("MINIO_REGION_NAME cannot be blank.")
        object.__setattr__(self, "region_name", region)

    def __repr__(self) -> str:
        return (
            "StorageSettings("
            f"backend={self.backend!r}, "
            f"endpoint_url={self.endpoint_url!r}, "
            "access_key=SecretValue('***'), "
            "secret_key=SecretValue('***'), "
            f"bucket_name={self.bucket_name!r}, "
            f"region_name={self.region_name!r})"
        )

    @classmethod
    def from_environ(cls, environ: Environ) -> StorageSettings:
        endpoint_url = (
            get_str(
                environ,
                "MINIO_SERVER_URL",
                default=DEFAULT_MINIO_ENDPOINT,
            )
            or DEFAULT_MINIO_ENDPOINT
        )
        access_key = get_secret(
            environ,
            "MINIO_ROOT_USER",
            default=DEFAULT_MINIO_ACCESS_KEY,
        )
        secret_key = get_secret(
            environ,
            "MINIO_ROOT_PASSWORD",
            default=DEFAULT_MINIO_SECRET_KEY,
        )
        if access_key is None or secret_key is None:
            raise ConfigurationError("MinIO credentials are required.")
        bucket_name = (
            get_str(
                environ,
                "MINIO_BUCKET",
                default=DEFAULT_MINIO_BUCKET,
            )
            or DEFAULT_MINIO_BUCKET
        )
        region_name = (
            get_str(
                environ,
                "MINIO_REGION_NAME",
                default=DEFAULT_MINIO_REGION,
            )
            or DEFAULT_MINIO_REGION
        )
        backend = (
            get_str(
                environ,
                "MEMOVI_OBJECT_STORAGE",
                default=DEFAULT_OBJECT_STORAGE_BACKEND,
            )
            or DEFAULT_OBJECT_STORAGE_BACKEND
        )
        return cls(
            endpoint_url=endpoint_url,
            access_key=access_key,
            secret_key=secret_key,
            bucket_name=bucket_name,
            region_name=region_name,
            backend=backend,
        )
