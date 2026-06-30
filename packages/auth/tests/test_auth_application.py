from datetime import UTC, datetime, timedelta

import pytest
from auth.application.commands import LoginUser, LoginUserCommand, LogoutUser, RegisterUser
from auth.application.commands.register_user import RegisterUserCommand
from auth.application.exceptions import (
    EmailAlreadyRegisteredError,
    InvalidCredentialsError,
    UnauthenticatedError,
)
from auth.application.queries import GetCurrentUser
from auth.domain.entities import Session, User
from auth.domain.repositories import SessionRepository, UserRepository
from auth.domain.value_objects import Email, PasswordHash, UserId


class InMemoryUserRepository(UserRepository):
    def __init__(self) -> None:
        self.users: dict[str, User] = {}

    def get_by_id(self, user_id: UserId) -> User | None:
        return self.users.get(user_id.value)

    def get_by_email(self, email: Email) -> User | None:
        for user in self.users.values():
            if user.email == email:
                return user
        return None

    def add(self, user: User) -> None:
        self.users[user.id.value] = user


class InMemorySessionRepository(SessionRepository):
    def __init__(self) -> None:
        self.sessions: dict[str, Session] = {}

    def get_by_token_hash(self, token_hash: str) -> Session | None:
        for session in self.sessions.values():
            if session.token_hash == token_hash:
                return session
        return None

    def add(self, session: Session) -> None:
        self.sessions[session.id] = session

    def save(self, session: Session) -> None:
        self.sessions[session.id] = session


class FakePasswordHasher:
    def hash(self, password: str) -> PasswordHash:
        return PasswordHash(f"$argon2id$fake${password}")

    def verify(self, password_hash: PasswordHash, password: str) -> bool:
        return password_hash.value == f"$argon2id$fake${password}"


class FakeSessionTokenService:
    def __init__(self) -> None:
        self._next = 0

    def new_token(self) -> str:
        self._next += 1
        return f"token-{self._next}"

    def token_hash(self, token: str) -> str:
        return f"hash:{token}"


def test_register_user_creates_user_and_session() -> None:
    users = InMemoryUserRepository()
    sessions = InMemorySessionRepository()
    tokens = FakeSessionTokenService()

    result = RegisterUser(
        users=users,
        sessions=sessions,
        password_hasher=FakePasswordHasher(),
        session_tokens=tokens,
        session_ttl=timedelta(days=30),
    ).execute(RegisterUserCommand(email="USER@example.com", password="correct horse battery"))

    assert result.user.email == "user@example.com"
    assert result.session_token == "token-1"
    assert users.get_by_email(Email("user@example.com")) is not None
    assert sessions.get_by_token_hash("hash:token-1") is not None


def test_register_user_rejects_duplicate_email() -> None:
    users = InMemoryUserRepository()
    sessions = InMemorySessionRepository()
    use_case = RegisterUser(
        users=users,
        sessions=sessions,
        password_hasher=FakePasswordHasher(),
        session_tokens=FakeSessionTokenService(),
        session_ttl=timedelta(days=30),
    )

    use_case.execute(RegisterUserCommand(email="user@example.com", password="password123"))

    with pytest.raises(EmailAlreadyRegisteredError):
        use_case.execute(RegisterUserCommand(email="USER@example.com", password="password123"))


def test_login_user_requires_matching_password() -> None:
    users = InMemoryUserRepository()
    sessions = InMemorySessionRepository()
    hasher = FakePasswordHasher()
    user = User.register(
        email=Email("user@example.com"),
        password_hash=hasher.hash("right-password"),
        now=datetime.now(UTC),
    )
    users.add(user)

    use_case = LoginUser(
        users=users,
        sessions=sessions,
        password_hasher=hasher,
        session_tokens=FakeSessionTokenService(),
        session_ttl=timedelta(days=30),
    )

    with pytest.raises(InvalidCredentialsError):
        use_case.execute(LoginUserCommand(email="user@example.com", password="wrong-password"))


def test_current_user_requires_active_session() -> None:
    users = InMemoryUserRepository()
    sessions = InMemorySessionRepository()
    tokens = FakeSessionTokenService()
    hasher = FakePasswordHasher()
    now = datetime.now(UTC)
    user = User.register(
        email=Email("user@example.com"),
        password_hash=hasher.hash("password123"),
        now=now,
    )
    users.add(user)
    sessions.add(
        Session(
            id="session-id",
            user_id=user.id,
            token_hash=tokens.token_hash("token"),
            created_at=now - timedelta(days=2),
            expires_at=now - timedelta(days=1),
        )
    )

    with pytest.raises(UnauthenticatedError):
        GetCurrentUser(users=users, sessions=sessions, session_tokens=tokens).execute("token")


def test_logout_revokes_existing_session() -> None:
    sessions = InMemorySessionRepository()
    tokens = FakeSessionTokenService()
    now = datetime.now(UTC)
    session = Session(
        id="session-id",
        user_id=UserId.new(),
        token_hash=tokens.token_hash("token"),
        created_at=now,
        expires_at=now + timedelta(days=1),
    )
    sessions.add(session)

    LogoutUser(sessions=sessions, session_tokens=tokens).execute("token")

    revoked = sessions.get_by_token_hash(tokens.token_hash("token"))
    assert revoked is not None
    assert revoked.revoked_at is not None
