from documents.application.ports import QueuedProcessingJob


class NoOpProcessingJobQueue:
    """Discards queued jobs when no background worker is configured."""

    def enqueue(
        self,
        processing_job_id: str,
        *,
        attempt: int = 1,
        request_id: str | None = None,
        workspace_id: str | None = None,
    ) -> None:
        return None

    async def dequeue(self) -> QueuedProcessingJob | None:
        return None

    async def close(self) -> None:
        return None
