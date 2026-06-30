from datetime import timedelta
from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session as OrmSession

from auth.application.commands import LoginUser, LogoutUser, RegisterUser
from auth.application.queries import GetCurrentUser
from auth.infrastructure.repositories import SqlAlchemySessionRepository, SqlAlchemyUserRepository
from auth.infrastructure.security import Argon2idPasswordHasher, SecureSessionTokenService

SESSION_COOKIE_NAME = "memovi_session"
SESSION_TTL = timedelta(days=30)


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
