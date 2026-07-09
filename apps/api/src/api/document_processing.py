import asyncio
import logging
from collections.abc import Callable

from documents.application.exceptions import ProcessingJobNotFoundError
from documents.application.ports import EventPublisher, ObjectStorage, ProcessingJobQueue
from documents.application.workers import DocumentProcessingWorker, DocumentProcessingWorkerConfig
from documents.infrastructure.events.noop_event_publisher import NoOpEventPublisher
from documents.infrastructure.queue import InMemoryProcessingJobQueue
from documents.infrastructure.storage import MinioObjectStorage
from fastapi import FastAPI
from sqlalchemy.orm import Session as OrmSession

from api.bootstrap import LOGGER_NAME

LOGGER = logging.getLogger(LOGGER_NAME)


def configure_document_processing(
    app: FastAPI,
    *,
    session_factory: Callable[[], OrmSession],
    queue: ProcessingJobQueue | None = None,
    worker_config: DocumentProcessingWorkerConfig | None = None,
    object_storage: ObjectStorage | None = None,
    event_publisher: EventPublisher | None = None,
) -> DocumentProcessingWorker:
    processing_queue = queue or InMemoryProcessingJobQueue()
    app.state.processing_job_queue = processing_queue

    worker = DocumentProcessingWorker(
        queue=processing_queue,
        session_factory=session_factory,
        object_storage=object_storage or MinioObjectStorage.from_env(),
        event_publisher=event_publisher or NoOpEventPublisher(),
        config=worker_config,
    )
    app.state.document_processing_worker = worker
    return worker


async def start_document_processing_worker(app: FastAPI) -> asyncio.Task[None]:
    worker: DocumentProcessingWorker = app.state.document_processing_worker
    task = asyncio.create_task(worker.run(), name="document-processing-worker")
    app.state.document_processing_worker_task = task
    LOGGER.info("Document processing worker started")
    return task


async def stop_document_processing_worker(app: FastAPI) -> None:
    worker: DocumentProcessingWorker = app.state.document_processing_worker
    task: asyncio.Task[None] = app.state.document_processing_worker_task

    await worker.shutdown()
    try:
        await task
    except ProcessingJobNotFoundError:
        LOGGER.warning("Document processing worker exited while a job was unavailable.")
    LOGGER.info("Document processing worker stopped")
