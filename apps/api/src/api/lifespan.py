import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from documents.application.ports import ObjectStorage
from documents.infrastructure.queue import InMemoryProcessingJobQueue
from documents.infrastructure.storage import InMemoryObjectStorage, MinioObjectStorage
from fastapi import FastAPI

from api.bootstrap import LOGGER_NAME, initialize_logging, validate_configuration
from api.database import create_session
from api.document_processing import (
    configure_document_processing,
    start_document_processing_worker,
    stop_document_processing_worker,
)


def _startup_object_storage() -> ObjectStorage:
    """Prefer MinIO, but fail fast to in-memory when local infra is unavailable."""
    try:
        return MinioObjectStorage.from_env()
    except Exception as exc:
        logging.getLogger(LOGGER_NAME).warning(
            "MinIO unavailable at startup (%s); using in-memory object storage.",
            exc,
        )
        return InMemoryObjectStorage()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    initialize_logging()
    validate_configuration()

    logger = logging.getLogger(LOGGER_NAME)
    if not hasattr(app.state, "document_processing_worker"):
        configure_document_processing(
            app,
            session_factory=create_session,
            queue=InMemoryProcessingJobQueue(),
            object_storage=_startup_object_storage(),
        )
    if not hasattr(app.state, "document_processing_worker_task"):
        await start_document_processing_worker(app)
    logger.info("Memovi API startup complete")

    yield

    if hasattr(app.state, "document_processing_worker_task"):
        await stop_document_processing_worker(app)
    logger.info("Memovi API shutdown complete")
