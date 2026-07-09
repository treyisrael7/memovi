import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from api.bootstrap import LOGGER_NAME, initialize_logging, validate_configuration
from api.database import create_session
from api.document_processing import (
    configure_document_processing,
    start_document_processing_worker,
    stop_document_processing_worker,
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    initialize_logging()
    validate_configuration()

    logger = logging.getLogger(LOGGER_NAME)
    if not hasattr(app.state, "document_processing_worker"):
        configure_document_processing(app, session_factory=create_session)
    if not hasattr(app.state, "document_processing_worker_task"):
        await start_document_processing_worker(app)
    logger.info("Memovi API startup complete")

    yield

    if hasattr(app.state, "document_processing_worker_task"):
        await stop_document_processing_worker(app)
    logger.info("Memovi API shutdown complete")
