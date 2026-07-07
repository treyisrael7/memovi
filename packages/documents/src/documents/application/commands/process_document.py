from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime

from documents.application.exceptions import (
    DocumentNotFoundError,
    DocumentVersionNotFoundError,
    InvalidProcessingStateError,
    ProcessingJobNotFoundError,
)
from documents.application.ports import EventPublisher, ObjectStorage, ProcessorRegistry
from documents.domain.entities import ProcessingJob
from documents.domain.enums import ProcessingStatus
from documents.domain.events import ProcessingCompleted, ProcessingFailed, ProcessingStarted
from documents.domain.exceptions import InvalidProcessingTransitionError
from documents.domain.repositories import DocumentRepository, ProcessingJobRepository
from documents.domain.services import normalize_text


@dataclass(frozen=True, slots=True)
class ProcessDocumentCommand:
    processing_job_id: str


@dataclass(frozen=True, slots=True)
class ProcessDocumentResult:
    processing_job_id: str
    processing_status: ProcessingStatus
    events: tuple[ProcessingStarted | ProcessingCompleted | ProcessingFailed, ...]


class ProcessDocument:
    """Synchronously transforms an immutable artifact into normalized text."""

    def __init__(
        self,
        *,
        documents: DocumentRepository,
        processing_jobs: ProcessingJobRepository,
        object_storage: ObjectStorage,
        processor_registry: ProcessorRegistry,
        event_publisher: EventPublisher,
    ) -> None:
        self._documents = documents
        self._processing_jobs = processing_jobs
        self._object_storage = object_storage
        self._processor_registry = processor_registry
        self._event_publisher = event_publisher

    def execute(self, command: ProcessDocumentCommand) -> ProcessDocumentResult:
        job = self._load_pending_job(command.processing_job_id)
        document = self._documents.get_by_id(job.document_id)
        if document is None:
            raise DocumentNotFoundError("Document was not found.")

        version = self._documents.get_version_by_id(job.document_version_id)
        if version is None:
            raise DocumentVersionNotFoundError("Document version was not found.")

        now = datetime.now(UTC)
        job = self._transition(job, lambda current: current.start(now=now))
        started_event = ProcessingStarted(
            document_id=job.document_id,
            processing_job_id=job.id,
            occurred_at=now,
        )
        self._event_publisher.publish(started_event)
        events: list[ProcessingStarted | ProcessingCompleted | ProcessingFailed] = [started_event]

        try:
            artifact = self._object_storage.get_object(version.storage_key)
            processor = self._processor_registry.processor_for(document.mime_type.value)
            extracted = processor.extract_text(artifact)

            job = self._transition(
                job,
                lambda current: current.advance_to_normalizing(now=datetime.now(UTC)),
            )

            normalized = normalize_text(extracted)
            self._documents.save_version(version.with_normalized_content(normalized))

            job = self._transition(job, lambda current: current.complete(now=datetime.now(UTC)))
            completed_event = ProcessingCompleted(
                document_id=job.document_id,
                processing_job_id=job.id,
                occurred_at=datetime.now(UTC),
            )
            self._event_publisher.publish(completed_event)
            events.append(completed_event)

            return ProcessDocumentResult(
                processing_job_id=job.id,
                processing_status=job.status,
                events=tuple(events),
            )
        except Exception as exc:
            return self._fail(job, reason=str(exc), prior_events=events)

    def _load_pending_job(self, processing_job_id: str) -> ProcessingJob:
        job = self._processing_jobs.get_by_id(processing_job_id)
        if job is None:
            raise ProcessingJobNotFoundError("Processing job was not found.")
        if job.status is not ProcessingStatus.PENDING:
            raise InvalidProcessingStateError("Processing job is not pending.")
        return job

    def _transition(
        self,
        job: ProcessingJob,
        transition: Callable[[ProcessingJob], ProcessingJob],
    ) -> ProcessingJob:
        try:
            updated = transition(job)
        except InvalidProcessingTransitionError as exc:
            raise InvalidProcessingStateError(str(exc)) from exc

        self._processing_jobs.save(updated)
        return updated

    def _fail(
        self,
        job: ProcessingJob,
        *,
        reason: str,
        prior_events: list[ProcessingStarted | ProcessingCompleted | ProcessingFailed],
    ) -> ProcessDocumentResult:
        failed_at = datetime.now(UTC)
        try:
            updated = job.fail(reason=reason, now=failed_at)
        except InvalidProcessingTransitionError as exc:
            raise InvalidProcessingStateError(str(exc)) from exc

        self._processing_jobs.save(updated)
        failed_event = ProcessingFailed(
            document_id=updated.document_id,
            processing_job_id=updated.id,
            occurred_at=failed_at,
            reason=reason,
        )
        self._event_publisher.publish(failed_event)
        prior_events.append(failed_event)

        return ProcessDocumentResult(
            processing_job_id=updated.id,
            processing_status=updated.status,
            events=tuple(prior_events),
        )
