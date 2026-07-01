from dataclasses import dataclass
from datetime import UTC, datetime

from documents.application.exceptions import InvalidProcessingStateError, ProcessingJobNotFoundError
from documents.domain.events import ProcessingCompleted
from documents.domain.exceptions import InvalidProcessingTransitionError
from documents.domain.repositories import ProcessingJobRepository


@dataclass(frozen=True, slots=True)
class CompleteProcessingCommand:
    processing_job_id: str


@dataclass(frozen=True, slots=True)
class CompleteProcessingResult:
    processing_job_id: str
    event: ProcessingCompleted


class CompleteProcessing:
    def __init__(self, *, processing_jobs: ProcessingJobRepository) -> None:
        self._processing_jobs = processing_jobs

    def execute(self, command: CompleteProcessingCommand) -> CompleteProcessingResult:
        job = self._processing_jobs.get_by_id(command.processing_job_id)
        if job is None:
            raise ProcessingJobNotFoundError("Processing job was not found.")

        now = datetime.now(UTC)
        try:
            updated = job.complete(now=now)
        except InvalidProcessingTransitionError as exc:
            raise InvalidProcessingStateError(str(exc)) from exc

        self._processing_jobs.save(updated)

        return CompleteProcessingResult(
            processing_job_id=updated.id,
            event=ProcessingCompleted(
                document_id=updated.document_id,
                processing_job_id=updated.id,
                occurred_at=now,
            ),
        )
