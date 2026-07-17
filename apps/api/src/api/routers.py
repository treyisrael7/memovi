from auth.api.dependencies import get_database_session as get_auth_database_session
from auth.api.router import router as auth_router
from documents.api.dependencies import get_database_session as get_documents_database_session
from documents.api.router import router as documents_router
from fastapi import FastAPI
from memovi_intelligence.api.router import router as conversations_router
from memovi_search.api.dependencies import get_database_session as get_search_database_session
from memovi_search.api.router import router as search_router

from api.database import database_session
from api.documents_session import build_documents_database_session
from api.health import router as health_router


def register_routers(app: FastAPI) -> None:
    app.dependency_overrides[get_auth_database_session] = database_session
    app.dependency_overrides[get_documents_database_session] = build_documents_database_session(
        database_session
    )
    app.dependency_overrides[get_search_database_session] = database_session
    app.include_router(auth_router)
    app.include_router(documents_router)
    app.include_router(conversations_router)
    app.include_router(search_router)
    app.include_router(health_router)
