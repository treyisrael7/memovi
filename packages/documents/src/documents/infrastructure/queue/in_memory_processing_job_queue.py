import asyncio
import queue

from documents.application.ports import QueuedProcessingJob


class InMemoryProcessingJobQueue:
    """Thread-safe in-memory queue for local development and integration tests."""

    def __init__(self) -> None:
        self._queue: queue.Queue[QueuedProcessingJob | None] = queue.Queue()
        self._closed = False

    def enqueue(
        self,
        processing_job_id: str,
        *,
        attempt: int = 1,
        request_id: str | None = None,
        workspace_id: str | None = None,
    ) -> None:
        if self._closed:
            raise RuntimeError("Processing job queue is closed.")

        self._queue.put(
            QueuedProcessingJob(
                processing_job_id=processing_job_id,
                attempt=attempt,
                request_id=request_id,
                workspace_id=workspace_id,
            )
        )

    async def dequeue(self) -> QueuedProcessingJob | None:
        while not self._closed:
            try:
                queued = self._queue.get_nowait()
            except queue.Empty:
                await asyncio.sleep(0.05)
                continue

            if queued is None:
                return None
            return queued

        return None

    async def close(self) -> None:
        if self._closed:
            return

        self._closed = True
        self._queue.put(None)
