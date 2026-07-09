from dataclasses import dataclass

from documents.application.ports import ProcessingJobQueue


@dataclass(frozen=True, slots=True)
class EnqueueDocumentProcessingCommand:
    processing_job_id: str


class EnqueueDocumentProcessing:
    """Schedules a persisted processing job for asynchronous execution."""

    def __init__(self, *, processing_job_queue: ProcessingJobQueue) -> None:
        self._processing_job_queue = processing_job_queue

    def execute(self, command: EnqueueDocumentProcessingCommand) -> None:
        self._processing_job_queue.enqueue(command.processing_job_id)
