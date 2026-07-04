from typing import Protocol


class ObjectStorage(Protocol):
    """Stores immutable document artifacts outside relational storage."""

    def put_object(self, *, key: str, content: bytes, content_type: str) -> None:
        raise NotImplementedError

    def get_object(self, key: str) -> bytes:
        raise NotImplementedError
