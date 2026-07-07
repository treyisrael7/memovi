from typing import Protocol


class ObjectStorage(Protocol):
    """Stores immutable document artifacts outside relational storage."""

    def put_object(self, *, key: str, content: bytes, content_type: str) -> None:
        raise NotImplementedError

    def get_object(self, key: str) -> bytes:
        raise NotImplementedError


class DocumentProcessor(Protocol):
    """Extracts textual content from an immutable document artifact."""

    def extract_text(self, content: bytes) -> str:
        raise NotImplementedError


class ProcessorRegistry(Protocol):
    """Resolves MIME-specific document processors."""

    def processor_for(self, mime_type: str) -> DocumentProcessor:
        raise NotImplementedError


class EventPublisher(Protocol):
    """Publishes domain events to downstream consumers."""

    def publish(self, event: object) -> None:
        raise NotImplementedError
