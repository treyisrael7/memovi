from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class QueuedProcessingJob:
    processing_job_id: str
    attempt: int = 1
    request_id: str | None = None
    workspace_id: str | None = None


class ProcessingJobQueue(Protocol):
    """Queues document processing jobs for asynchronous execution."""

    def enqueue(
        self,
        processing_job_id: str,
        *,
        attempt: int = 1,
        request_id: str | None = None,
        workspace_id: str | None = None,
    ) -> None:
        raise NotImplementedError

    async def dequeue(self) -> QueuedProcessingJob | None:
        """Return the next queued job, or ``None`` when the queue is closed."""
        raise NotImplementedError

    async def close(self) -> None:
        """Stop accepting work and unblock waiting consumers."""
        raise NotImplementedError


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
