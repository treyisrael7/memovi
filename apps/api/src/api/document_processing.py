import asyncio
import logging
from collections.abc import Callable

from documents.application.exceptions import ProcessingJobNotFoundError
from documents.application.ports import EventPublisher, ObjectStorage, ProcessingJobQueue
from documents.application.workers import DocumentProcessingWorker, DocumentProcessingWorkerConfig
from documents.infrastructure.queue import SqlAlchemyProcessingJobQueue
from fastapi import FastAPI
from sqlalchemy.orm import Session as OrmSession

from api.bootstrap import LOGGER_NAME
from api.embedding_composition import configure_embedding_provider
from api.events import InProcessEventDispatcher, TransactionScopedEventPublisher
from api.memory_integration import configure_event_dispatch

LOGGER = logging.getLogger(LOGGER_NAME)

MEMORY_STORAGE_LABEL = "Development object storage: In-memory"
MINIO_STORAGE_LABEL = "Persistent object storage: MinIO"


def describe_object_storage(
    storage: ObjectStorage,
    *,
    backend: str | None = None,
) -> str:
    """Operator-facing backend label. Does not include endpoints or credentials."""
    kind = (backend or "").strip().lower()
    if kind == "memory" or type(storage).__name__ == "InMemoryObjectStorage":
        return MEMORY_STORAGE_LABEL
    return MINIO_STORAGE_LABEL


def configure_document_processing(
    app: FastAPI,
    *,
    session_factory: Callable[[], OrmSession],
    object_storage: ObjectStorage,
    queue: ProcessingJobQueue | None = None,
    worker_config: DocumentProcessingWorkerConfig | None = None,
    event_publisher: EventPublisher | None = None,
    event_dispatcher: InProcessEventDispatcher | None = None,
    storage_backend: str | None = None,
) -> DocumentProcessingWorker:
    processing_queue = queue or SqlAlchemyProcessingJobQueue(
        session_factory,
        poll_interval_seconds=(
            worker_config.poll_interval_seconds if worker_config is not None else 0.25
        ),
    )
    app.state.processing_job_queue = processing_queue

    if event_dispatcher is not None:
        app.state.event_dispatcher = event_dispatcher

    if event_publisher is None:
        dispatcher = event_dispatcher or getattr(app.state, "event_dispatcher", None)
        if dispatcher is None:
            embedding_provider = getattr(app.state, "embedding_provider", None)
            if embedding_provider is None:
                embedding_provider = configure_embedding_provider(app)
            dispatcher = configure_event_dispatch(
                session_factory=session_factory,
                embedding_provider=embedding_provider,
            )
            app.state.event_dispatcher = dispatcher
        event_publisher = TransactionScopedEventPublisher(dispatcher)

    worker = DocumentProcessingWorker(
        queue=processing_queue,
        session_factory=session_factory,
        object_storage=object_storage,
        event_publisher=event_publisher,
        config=worker_config,
    )
    app.state.document_processing_worker = worker
    app.state.object_storage = object_storage
    app.state.object_storage_backend = (storage_backend or "").strip().lower() or (
        "memory" if type(object_storage).__name__ == "InMemoryObjectStorage" else "minio"
    )
    app.state.object_storage_label = describe_object_storage(
        object_storage,
        backend=app.state.object_storage_backend,
    )
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
