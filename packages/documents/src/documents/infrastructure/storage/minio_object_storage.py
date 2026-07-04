import os

import boto3
from botocore.exceptions import ClientError


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
        self._client = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region_name,
        )
        self._ensure_bucket_exists()

    @classmethod
    def from_env(cls) -> MinioObjectStorage:
        endpoint_url = os.getenv("MINIO_SERVER_URL", "http://127.0.0.1:9000")
        access_key = os.getenv("MINIO_ROOT_USER", "memovi_minio_admin")
        secret_key = os.getenv("MINIO_ROOT_PASSWORD", "memovi_local_minio_5c7f1e9a3b6d4a82")
        bucket_name = os.getenv("MINIO_BUCKET", "memovi-documents")
        region_name = os.getenv("MINIO_REGION_NAME", "us-east-1")
        return cls(
            endpoint_url=endpoint_url,
            access_key=access_key,
            secret_key=secret_key,
            bucket_name=bucket_name,
            region_name=region_name,
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

    def _ensure_bucket_exists(self) -> None:
        try:
            self._client.head_bucket(Bucket=self._bucket_name)
        except ClientError as exc:
            error_code = exc.response.get("Error", {}).get("Code")
            if error_code not in {"404", "NoSuchBucket", "403"}:
                raise
            self._client.create_bucket(Bucket=self._bucket_name)
