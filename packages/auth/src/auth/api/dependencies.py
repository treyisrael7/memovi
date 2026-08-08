import os
from typing import Annotated

from fastapi import Cookie, Depends, HTTPException, Request, status
from memovi_config.settings.auth import AuthSettings
from sqlalchemy.orm import Session as OrmSession

from auth.application.commands import LoginUser, LogoutUser, RegisterUser
from auth.application.dto import AuthenticatedPrincipal
from auth.application.exceptions import UnauthenticatedError
from auth.application.queries import GetCurrentUser, ResolveAuthenticatedPrincipal
from auth.infrastructure.repositories import SqlAlchemySessionRepository, SqlAlchemyUserRepository
from auth.infrastructure.security import Argon2idPasswordHasher, SecureSessionTokenService

_AUTH_SETTINGS = AuthSettings.from_environ(os.environ)
SESSION_COOKIE_NAME = _AUTH_SETTINGS.session_cookie_name
SESSION_TTL = _AUTH_SETTINGS.session_ttl


def get_database_session() -> OrmSession:
    raise RuntimeError("Auth database session dependency was not configured.")


DatabaseSession = Annotated[OrmSession, Depends(get_database_session)]


def get_register_user(session: DatabaseSession) -> RegisterUser:
    return RegisterUser(
        users=SqlAlchemyUserRepository(session),
        sessions=SqlAlchemySessionRepository(session),
        password_hasher=Argon2idPasswordHasher(),
        session_tokens=SecureSessionTokenService(),
        session_ttl=SESSION_TTL,
    )


def get_login_user(session: DatabaseSession) -> LoginUser:
    return LoginUser(
        users=SqlAlchemyUserRepository(session),
        sessions=SqlAlchemySessionRepository(session),
        password_hasher=Argon2idPasswordHasher(),
        session_tokens=SecureSessionTokenService(),
        session_ttl=SESSION_TTL,
    )


def get_logout_user(session: DatabaseSession) -> LogoutUser:
    return LogoutUser(
        sessions=SqlAlchemySessionRepository(session),
        session_tokens=SecureSessionTokenService(),
    )


def get_current_user_query(session: DatabaseSession) -> GetCurrentUser:
    return GetCurrentUser(
        users=SqlAlchemyUserRepository(session),
        sessions=SqlAlchemySessionRepository(session),
        session_tokens=SecureSessionTokenService(),
    )


def get_resolve_authenticated_principal(
    session: DatabaseSession,
) -> ResolveAuthenticatedPrincipal:
    return ResolveAuthenticatedPrincipal(
        users=SqlAlchemyUserRepository(session),
        sessions=SqlAlchemySessionRepository(session),
        session_tokens=SecureSessionTokenService(),
    )


def require_authenticated_principal(
    request: Request,
    resolver: Annotated[
        ResolveAuthenticatedPrincipal,
        Depends(get_resolve_authenticated_principal),
    ],
    session_token: Annotated[str | None, Cookie(alias=SESSION_COOKIE_NAME)] = None,
) -> AuthenticatedPrincipal:
    """Require an authenticated principal for non-public API handlers."""
    cached = getattr(request.state, "authenticated_principal", None)
    if isinstance(cached, AuthenticatedPrincipal):
        return cached
    try:
        principal = resolver.execute(session_token)
    except UnauthenticatedError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication is required.",
        ) from exc
    request.state.authenticated_principal = principal
    return principal
