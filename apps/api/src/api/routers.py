from auth.api.dependencies import get_database_session as get_auth_database_session
from auth.api.router import router as auth_router
from documents.api.dependencies import get_database_session as get_documents_database_session
from documents.api.router import router as documents_router
from fastapi import FastAPI
from memovi_intelligence.api.dependencies import (
    get_conversation_repository,
    get_database_session as get_intelligence_database_session,
    get_knowledge_retriever,
)
from memovi_intelligence.api.router import router as conversations_router
from memovi_search.api.dependencies import get_database_session as get_search_database_session
from memovi_search.api.router import router as search_router

from api.database import database_session
from api.documents_session import build_documents_database_session
from api.health import router as health_router
from api.intelligence_integration import (
    get_search_knowledge_retriever,
    get_sqlalchemy_conversation_repository,
)


def register_routers(app: FastAPI) -> None:
    app.dependency_overrides[get_auth_database_session] = database_session
    app.dependency_overrides[get_documents_database_session] = build_documents_database_session(
        database_session
    )
    app.dependency_overrides[get_search_database_session] = database_session
    app.dependency_overrides[get_intelligence_database_session] = database_session
    app.dependency_overrides[get_conversation_repository] = get_sqlalchemy_conversation_repository
    app.dependency_overrides[get_knowledge_retriever] = get_search_knowledge_retriever
    app.include_router(auth_router)
    app.include_router(documents_router)
    app.include_router(conversations_router)
    app.include_router(search_router)
    app.include_router(health_router)
