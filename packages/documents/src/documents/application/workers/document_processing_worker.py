import asyncio
import logging
import time
from collections.abc import Callable
from contextvars import Token
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from memovi_observability import (
    RequestContext,
    bind_request_context,
    clear_request_context,
    get_metrics_recorder,
)
from memovi_shared import InvalidWorkspaceIdError, WorkspaceId
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


def _bind_queued_request_context(queued: QueuedProcessingJob) -> Token[Any] | None:
    """Restore request/workspace identity for worker logs and diagnostic events."""
    if queued.request_id is None and queued.workspace_id is None:
        return None
    workspace_id: WorkspaceId | None = None
    if queued.workspace_id is not None:
        try:
            workspace_id = WorkspaceId(queued.workspace_id)
        except InvalidWorkspaceIdError:
            workspace_id = None
    return bind_request_context(
        RequestContext.create(
            request_id=queued.request_id,
            workspace_id=workspace_id,
        )
    )


def _clear_queued_request_context(token: Token[Any] | None) -> None:
    if token is not None:
        clear_request_context(token)


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
            # Do not wrap dequeue in wait_for: cancelling asyncio.to_thread(queue.get)
            # can consume a queued job without processing it.
            queued = await self._queue.dequeue()
            if queued is None:
                break

            try:
                # Process on the event-loop thread. asyncio.to_thread + StaticPool
                # SQLite shares one connection across threads and corrupts results.
                self._process_queued_job(queued)
            except ProcessingJobNotFoundError:
                LOGGER.warning(
                    "Skipping processing job %s because it is not available yet.",
                    queued.processing_job_id,
                )

    async def shutdown(self) -> None:
        self._shutdown.set()
        await self._queue.close()

    def _process_queued_job(self, queued: QueuedProcessingJob) -> None:
        context_token = _bind_queued_request_context(queued)
        metrics = get_metrics_recorder()
        started = time.perf_counter()
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
                flush = getattr(self._event_publisher, "flush", None)
                if flush is not None:
                    flush()
            except TransientDocumentProcessingError as exc:
                session.rollback()
                self._handle_transient_failure(queued, reason=str(exc))
                return

            duration_ms = (time.perf_counter() - started) * 1000.0
            metrics.timing(
                "memovi.documents.processing.duration_ms",
                duration_ms,
                tags={"status": result.processing_status.value},
            )
            if result.processing_status is ProcessingStatus.FAILED:
                metrics.increment("memovi.documents.processing.failed")
                LOGGER.warning(
                    "Processing job %s failed permanently: %s",
                    queued.processing_job_id,
                    result.events[-1],
                )
            elif result.processing_status is ProcessingStatus.COMPLETED:
                metrics.increment("memovi.documents.processing.completed")
                metrics.increment("memovi.documents.processing.throughput")
        except Exception:
            session.rollback()
            metrics.increment("memovi.documents.processing.failed")
            LOGGER.exception(
                "Unexpected error while processing job %s",
                queued.processing_job_id,
            )
            raise
        finally:
            session.close()
            _clear_queued_request_context(context_token)

    def _handle_transient_failure(self, queued: QueuedProcessingJob, *, reason: str) -> None:
        metrics = get_metrics_recorder()
        if queued.attempt >= self._config.max_retries:
            self._fail_exhausted_job(queued.processing_job_id, reason=reason)
            metrics.increment("memovi.documents.processing.failed")
            return

        if not self._reset_job_to_pending(queued.processing_job_id):
            return

        next_attempt = queued.attempt + 1
        self._queue.enqueue(
            queued.processing_job_id,
            attempt=next_attempt,
            request_id=queued.request_id,
            workspace_id=queued.workspace_id,
        )
        metrics.increment(
            "memovi.documents.processing.retries",
            tags={"attempt": str(next_attempt)},
        )
        LOGGER.info(
            "Scheduled retry %s/%s for processing job %s",
            next_attempt,
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
