import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from documents.application.ports import ObjectStorage
from documents.infrastructure.queue import SqlAlchemyProcessingJobQueue
from documents.infrastructure.storage import InMemoryObjectStorage, MinioObjectStorage
from fastapi import FastAPI
from memovi_config.exceptions import ConfigurationError
from memovi_config.settings import Settings
from memovi_config.settings.storage import ObjectStorageBackend

from api.bootstrap import LOGGER_NAME, initialize_logging, validate_configuration
from api.database import create_session
from api.document_processing import (
    configure_document_processing,
    describe_object_storage,
    start_document_processing_worker,
    stop_document_processing_worker,
)
from api.embedding_composition import configure_embedding_provider

_MINIO_UNAVAILABLE = (
    "Persistent object storage is required but MinIO is unavailable ({error}). "
    "Start MinIO with `docker compose up -d` or `task docker-up`, then confirm "
    "MINIO_SERVER_URL. For local development only, set MEMOVI_OBJECT_STORAGE=memory "
    "with MEMOVI_ENV=local — in-memory storage is ephemeral and loses files on restart."
)


def startup_object_storage(settings: Settings) -> ObjectStorage:
    """Select object storage from explicit configuration. Never falls back silently."""
    logger = logging.getLogger(LOGGER_NAME)
    if settings.storage.backend == ObjectStorageBackend.MEMORY:
        storage: ObjectStorage = InMemoryObjectStorage()
        logger.info(describe_object_storage(storage, backend=settings.storage.backend))
        return storage
    try:
        storage = MinioObjectStorage.from_env()
    except Exception as exc:
        raise ConfigurationError(_MINIO_UNAVAILABLE.format(error=str(exc))) from exc
    logger.info(describe_object_storage(storage, backend=settings.storage.backend))
    return storage


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    initialize_logging()
    settings = validate_configuration()
    if not hasattr(app.state, "embedding_provider"):
        configure_embedding_provider(app)

    logger = logging.getLogger(LOGGER_NAME)
    if not hasattr(app.state, "document_processing_worker"):
        configure_document_processing(
            app,
            session_factory=create_session,
            queue=SqlAlchemyProcessingJobQueue(create_session),
            object_storage=startup_object_storage(settings),
            storage_backend=settings.storage.backend,
        )
    if not hasattr(app.state, "document_processing_worker_task"):
        await start_document_processing_worker(app)
    logger.info("Memovi API startup complete")

    yield

    if hasattr(app.state, "document_processing_worker_task"):
        await stop_document_processing_worker(app)
    logger.info("Memovi API shutdown complete")
