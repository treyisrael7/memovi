import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from api.bootstrap import LOGGER_NAME, initialize_logging, validate_configuration


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    initialize_logging()
    validate_configuration()

    logger = logging.getLogger(LOGGER_NAME)
    logger.info("Memovi API startup complete")

    yield

    logger.info("Memovi API shutdown complete")
