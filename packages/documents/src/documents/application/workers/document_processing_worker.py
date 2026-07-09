import asyncio
import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.orm import Session as OrmSession

from documents.application.commands.fail_processing import FailProcessing, FailProcessingCommand
from documents.application.commands.process_document import ProcessDocument, ProcessDocumentCommand
from documents.application.exceptions import (
    ProcessingJobNotFoundError,
    TransientDocumentProcessingError,
)
from documents.application.ports import (
    EventPublisher,
    ObjectStorage,
    ProcessingJobQueue,
    QueuedProcessingJob,
)
from documents.domain.enums import ProcessingStatus
from documents.domain.exceptions import InvalidProcessingTransitionError
from documents.infrastructure.processors import DefaultProcessorRegistry
from documents.infrastructure.repositories import (
    SqlAlchemyDocumentRepository,
    SqlAlchemyProcessingJobRepository,
)

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class DocumentProcessingWorkerConfig:
    max_retries: int = 3
    poll_interval_seconds: float = 0.25


class DocumentProcessingWorker:
    """Executes queued document processing jobs outside the request path."""

    def __init__(
        self,
        *,
        queue: ProcessingJobQueue,
        session_factory: Callable[[], OrmSession],
        object_storage: ObjectStorage,
        event_publisher: EventPublisher,
        config: DocumentProcessingWorkerConfig | None = None,
    ) -> None:
        self._queue = queue
        self._session_factory = session_factory
        self._object_storage = object_storage
        self._event_publisher = event_publisher
        self._config = config or DocumentProcessingWorkerConfig()
        self._shutdown = asyncio.Event()

    async def run(self) -> None:
        while not self._shutdown.is_set():
            try:
                queued = await asyncio.wait_for(
                    self._queue.dequeue(),
                    timeout=self._config.poll_interval_seconds,
                )
            except TimeoutError:
                continue

            if queued is None:
                break

            try:
                await asyncio.to_thread(self._process_queued_job, queued)
            except ProcessingJobNotFoundError:
                LOGGER.warning(
                    "Skipping processing job %s because it is not available yet.",
                    queued.processing_job_id,
                )

    async def shutdown(self) -> None:
        self._shutdown.set()
        await self._queue.close()

    def _process_queued_job(self, queued: QueuedProcessingJob) -> None:
        session = self._session_factory()
        try:
            process_document = ProcessDocument(
                documents=SqlAlchemyDocumentRepository(session),
                processing_jobs=SqlAlchemyProcessingJobRepository(session),
                object_storage=self._object_storage,
                processor_registry=DefaultProcessorRegistry(),
                event_publisher=self._event_publisher,
            )

            try:
                result = process_document.execute(
                    ProcessDocumentCommand(processing_job_id=queued.processing_job_id),
                )
                session.commit()
            except TransientDocumentProcessingError as exc:
                session.rollback()
                self._handle_transient_failure(queued, reason=str(exc))
                return

            if result.processing_status is ProcessingStatus.FAILED:
                LOGGER.warning(
                    "Processing job %s failed permanently: %s",
                    queued.processing_job_id,
                    result.events[-1],
                )
        except Exception:
            session.rollback()
            LOGGER.exception(
                "Unexpected error while processing job %s",
                queued.processing_job_id,
            )
            raise
        finally:
            session.close()

    def _handle_transient_failure(self, queued: QueuedProcessingJob, *, reason: str) -> None:
        if queued.attempt >= self._config.max_retries:
            self._fail_exhausted_job(queued.processing_job_id, reason=reason)
            return

        if not self._reset_job_to_pending(queued.processing_job_id):
            return

        self._queue.enqueue(
            queued.processing_job_id,
            attempt=queued.attempt + 1,
        )
        LOGGER.info(
            "Scheduled retry %s/%s for processing job %s",
            queued.attempt + 1,
            self._config.max_retries,
            queued.processing_job_id,
        )

    def _reset_job_to_pending(self, processing_job_id: str) -> bool:
        session = self._session_factory()
        try:
            repository = SqlAlchemyProcessingJobRepository(session)
            job = repository.get_by_id(processing_job_id)
            if job is None:
                LOGGER.error("Processing job %s was not found for retry.", processing_job_id)
                return False

            try:
                updated = job.reset_to_pending(now=datetime.now(UTC))
            except InvalidProcessingTransitionError:
                LOGGER.exception(
                    "Processing job %s could not be reset for retry.",
                    processing_job_id,
                )
                return False

            repository.save(updated)
            session.commit()
            return True
        except Exception:
            session.rollback()
            LOGGER.exception(
                "Failed to reset processing job %s for retry.",
                processing_job_id,
            )
            raise
        finally:
            session.close()

    def _fail_exhausted_job(self, processing_job_id: str, *, reason: str) -> None:
        session = self._session_factory()
        try:
            fail_processing = FailProcessing(
                processing_jobs=SqlAlchemyProcessingJobRepository(session),
            )
            result = fail_processing.execute(
                FailProcessingCommand(
                    processing_job_id=processing_job_id,
                    reason=reason,
                ),
            )
            self._event_publisher.publish(result.event)
            session.commit()
            LOGGER.error(
                "Processing job %s failed after %s attempts: %s",
                processing_job_id,
                self._config.max_retries,
                reason,
            )
        except Exception:
            session.rollback()
            LOGGER.exception(
                "Failed to mark processing job %s as failed after retries were exhausted.",
                processing_job_id,
            )
            raise
        finally:
            session.close()
