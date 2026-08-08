from auth.api.dependencies import SESSION_TTL
from auth.api.dependencies import get_database_session as get_auth_database_session
from auth.api.dependencies import get_register_user as get_auth_register_user
from auth.api.router import router as auth_router
from auth.application.commands import RegisterUser
from auth.application.dto import AuthenticatedPrincipal
from auth.infrastructure.repositories import SqlAlchemySessionRepository, SqlAlchemyUserRepository
from auth.infrastructure.security import Argon2idPasswordHasher, SecureSessionTokenService
from documents.api.dependencies import get_active_workspace_id as get_documents_workspace_id
from documents.api.dependencies import get_database_session as get_documents_database_session
from documents.api.router import router as documents_router
from fastapi import Depends, FastAPI, Request
from memovi_automation.api.dependencies import (
    get_active_workspace_id as get_automation_workspace_id,
)
from memovi_automation.api.dependencies import (
    get_authenticated_execution_context as get_automation_auth_context,
)
from memovi_automation.api.router import router as capabilities_router
from memovi_automation.api.workflow_router import router as workflows_router
from memovi_automation.domain.value_objects.authenticated_execution_context import (
    AuthenticatedExecutionContext,
)
from memovi_connectors.api.dependencies import (
    get_active_workspace_id as get_connectors_workspace_id,
)
from memovi_connectors.api.dependencies import (
    get_database_session as get_connectors_database_session,
)
from memovi_connectors.api.dependencies import (
    get_filesystem_folder_service as get_connectors_filesystem_folder_service,
)
from memovi_connectors.api.router import router as connectors_router
from memovi_connectors.application.services.filesystem_folder_service import FilesystemFolderService
from memovi_intelligence.api.dependencies import (
    get_active_workspace_id as get_intelligence_workspace_id,
)
from memovi_intelligence.api.dependencies import (
    get_conversation_repository,
    get_execution_caller_identity,
    get_knowledge_retriever,
)
from memovi_intelligence.api.dependencies import (
    get_database_session as get_intelligence_database_session,
)
from memovi_intelligence.api.router import router as conversations_router
from memovi_intelligence.application.ports_capability_execution import ExecutionCallerIdentity
from memovi_memory.api.collections_router import router as collections_router
from memovi_memory.api.dependencies import get_active_workspace_id as get_memory_workspace_id
from memovi_memory.api.dependencies import get_collection_service as get_memory_collection_service
from memovi_memory.api.dependencies import get_database_session as get_memory_database_session
from memovi_memory.api.router import router as memory_router
from memovi_search.api.dependencies import get_active_workspace_id as get_search_workspace_id
from memovi_search.api.dependencies import get_database_session as get_search_database_session
from memovi_search.api.router import (
    get_collection_search_membership_resolver as get_search_collection_resolver,
)
from memovi_search.api.router import router as search_router
from memovi_shared import WorkspaceId
from memovi_workspace.api.dependencies import get_authenticated_user_id
from memovi_workspace.api.dependencies import get_database_session as get_workspace_database_session
from memovi_workspace.api.dependencies import get_user_directory as get_workspace_user_directory
from memovi_workspace.api.router import router as workspace_router
from memovi_workspace.application.ports import UserDirectoryPort
from sqlalchemy.orm import Session as OrmSession

from api.auth_context import (
    build_authenticated_execution_context,
    get_authenticated_principal,
)
from api.authorization import RequestScopedMembershipEnroller, build_user_directory
from api.capability_framework import configure_capability_execution
from api.connector_dependencies import build_filesystem_folder_service
from api.connector_framework import configure_connector_framework
from api.database import database_session
from api.documents_session import build_documents_database_session
from api.health import router as health_router
from api.intelligence_integration import (
    get_search_knowledge_retriever,
    get_sqlalchemy_conversation_repository,
)
from api.workspace_context import get_active_workspace_id


def _workspace_user_directory(
    session: OrmSession = Depends(get_workspace_database_session),
) -> UserDirectoryPort:
    return build_user_directory(session)


def _register_user(
    session: OrmSession = Depends(get_auth_database_session),
) -> RegisterUser:
    return RegisterUser(
        users=SqlAlchemyUserRepository(session),
        sessions=SqlAlchemySessionRepository(session),
        password_hasher=Argon2idPasswordHasher(),
        session_tokens=SecureSessionTokenService(),
        session_ttl=SESSION_TTL,
        on_registered=RequestScopedMembershipEnroller(session),
    )


def _authenticated_user_id(
    principal: AuthenticatedPrincipal = Depends(get_authenticated_principal),
) -> str:
    return principal.user_id


def _automation_auth_context(
    request: Request,
    principal: AuthenticatedPrincipal = Depends(get_authenticated_principal),
    workspace_id: WorkspaceId = Depends(get_active_workspace_id),
) -> AuthenticatedExecutionContext:
    return build_authenticated_execution_context(
        principal=principal,
        workspace_id=workspace_id,
        request=request,
        source="api",
    )


def _execution_caller_identity(
    request: Request,
    principal: AuthenticatedPrincipal = Depends(get_authenticated_principal),
) -> ExecutionCallerIdentity:
    context = build_authenticated_execution_context(
        principal=principal,
        workspace_id=WorkspaceId.default(),
        request=request,
        source="intelligence",
    )
    return ExecutionCallerIdentity(
        user_id=context.user_id,
        session_id=context.session_id,
        request_id=context.request_id,
    )


def _filesystem_folder_service(
    request: Request,
    session: OrmSession = Depends(get_connectors_database_session),
) -> FilesystemFolderService:
    return build_filesystem_folder_service(
        request,
        session,
        request.app.state.connector_scheduler,
    )


def register_routers(app: FastAPI) -> None:
    configure_capability_execution(app)
    configure_connector_framework(app)
    documents_session_dep = build_documents_database_session(database_session)
    app.dependency_overrides[get_auth_database_session] = database_session
    app.dependency_overrides[get_auth_register_user] = _register_user
    app.dependency_overrides[get_documents_database_session] = documents_session_dep
    app.dependency_overrides[get_connectors_database_session] = documents_session_dep
    app.dependency_overrides[get_connectors_filesystem_folder_service] = _filesystem_folder_service
    app.dependency_overrides[get_memory_database_session] = database_session
    app.dependency_overrides[get_search_database_session] = database_session
    app.dependency_overrides[get_intelligence_database_session] = database_session
    app.dependency_overrides[get_workspace_database_session] = database_session
    app.dependency_overrides[get_workspace_user_directory] = _workspace_user_directory
    app.dependency_overrides[get_documents_workspace_id] = get_active_workspace_id
    app.dependency_overrides[get_connectors_workspace_id] = get_active_workspace_id
    app.dependency_overrides[get_memory_workspace_id] = get_active_workspace_id
    app.dependency_overrides[get_search_workspace_id] = get_active_workspace_id
    app.dependency_overrides[get_intelligence_workspace_id] = get_active_workspace_id
    app.dependency_overrides[get_automation_workspace_id] = get_active_workspace_id
    app.dependency_overrides[get_authenticated_user_id] = _authenticated_user_id
    app.dependency_overrides[get_automation_auth_context] = _automation_auth_context
    app.dependency_overrides[get_execution_caller_identity] = _execution_caller_identity
    app.dependency_overrides[get_conversation_repository] = get_sqlalchemy_conversation_repository
    app.dependency_overrides[get_knowledge_retriever] = get_search_knowledge_retriever
    app.dependency_overrides[get_search_collection_resolver] = get_memory_collection_service
    app.include_router(auth_router)
    app.include_router(workspace_router)
    app.include_router(documents_router)
    app.include_router(connectors_router)
    app.include_router(memory_router)
    app.include_router(collections_router)
    app.include_router(capabilities_router)
    app.include_router(workflows_router)
    app.include_router(conversations_router)
    app.include_router(search_router)
    app.include_router(health_router)
