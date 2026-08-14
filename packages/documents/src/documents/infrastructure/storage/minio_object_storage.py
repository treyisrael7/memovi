import os

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
from memovi_config.settings.storage import StorageSettings


class MinioObjectStorage:
    """S3-compatible object storage adapter backed by MinIO."""

    def __init__(
        self,
        *,
        endpoint_url: str,
        access_key: str,
        secret_key: str,
        bucket_name: str,
        region_name: str = "us-east-1",
    ) -> None:
        self._bucket_name = bucket_name
        # Keep startup/probes snappy when MinIO is down (tests, offline local runs).
        self._client = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region_name,
            config=Config(
                connect_timeout=1,
                read_timeout=1,
                retries={"max_attempts": 1, "mode": "standard"},
            ),
        )
        self._ensure_bucket_exists()

    @classmethod
    def from_env(cls) -> MinioObjectStorage:
        storage = StorageSettings.from_environ(os.environ)
        return cls(
            endpoint_url=storage.endpoint_url,
            access_key=storage.access_key.get_secret_value(),
            secret_key=storage.secret_key.get_secret_value(),
            bucket_name=storage.bucket_name,
            region_name=storage.region_name,
        )

    def put_object(self, *, key: str, content: bytes, content_type: str) -> None:
        self._client.put_object(
            Bucket=self._bucket_name,
            Key=key,
            Body=content,
            ContentType=content_type,
        )

    def get_object(self, key: str) -> bytes:
        response = self._client.get_object(Bucket=self._bucket_name, Key=key)
        body = response["Body"].read()
        if not isinstance(body, bytes):
            raise TypeError("Object storage response body must be bytes.")
        return body

    def delete_object(self, key: str) -> None:
        self._client.delete_object(Bucket=self._bucket_name, Key=key)

    def check_available(self) -> None:
        """Fail fast when MinIO cannot be reached (startup and readiness)."""
        self._client.head_bucket(Bucket=self._bucket_name)

    def _ensure_bucket_exists(self) -> None:
        try:
            self._client.head_bucket(Bucket=self._bucket_name)
        except ClientError as exc:
            error_code = exc.response.get("Error", {}).get("Code")
            if error_code not in {"404", "NoSuchBucket", "403"}:
                raise
            self._client.create_bucket(Bucket=self._bucket_name)
