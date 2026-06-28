from fastapi import FastAPI

from api.bootstrap import project_metadata
from api.lifespan import lifespan
from api.middleware import register_middleware
from api.routers import register_routers


def create_app() -> FastAPI:
    metadata = project_metadata()

    app = FastAPI(
        title=metadata["title"],
        description=metadata["description"],
        version=metadata["version"],
        lifespan=lifespan,
    )

    register_middleware(app)
    register_routers(app)

    return app
