from dataclasses import dataclass
from datetime import UTC, datetime

from documents.application.exceptions import InvalidProcessingStateError, ProcessingJobNotFoundError
from documents.domain.events import ProcessingFailed
from documents.domain.exceptions import InvalidProcessingTransitionError
from documents.domain.repositories import ProcessingJobRepository


@dataclass(frozen=True, slots=True)
class FailProcessingCommand:
    processing_job_id: str
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class FailProcessingResult:
    processing_job_id: str
    event: ProcessingFailed


class FailProcessing:
    def __init__(self, *, processing_jobs: ProcessingJobRepository) -> None:
        self._processing_jobs = processing_jobs

    def execute(self, command: FailProcessingCommand) -> FailProcessingResult:
        job = self._processing_jobs.get_by_id(command.processing_job_id)
        if job is None:
            raise ProcessingJobNotFoundError("Processing job was not found.")

        now = datetime.now(UTC)
        try:
            updated = job.fail(reason=command.reason, now=now)
        except InvalidProcessingTransitionError as exc:
            raise InvalidProcessingStateError(str(exc)) from exc

        self._processing_jobs.save(updated)

        return FailProcessingResult(
            processing_job_id=updated.id,
            event=ProcessingFailed(
                document_id=updated.document_id,
                processing_job_id=updated.id,
                occurred_at=now,
                reason=command.reason,
            ),
        )
