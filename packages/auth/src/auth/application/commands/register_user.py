import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from auth.application.dto import UserDto
from auth.application.exceptions import EmailAlreadyRegisteredError
from auth.application.ports import PasswordHasher, SessionTokenService
from auth.domain.entities import Session, User
from auth.domain.repositories import SessionRepository, UserRepository
from auth.domain.value_objects import Email


@dataclass(frozen=True, slots=True)
class RegisterUserCommand:
    email: str
    password: str


@dataclass(frozen=True, slots=True)
class AuthenticatedUserResult:
    user: UserDto
    session_token: str
    session_expires_at: datetime


class RegisterUser:
    def __init__(
        self,
        *,
        users: UserRepository,
        sessions: SessionRepository,
        password_hasher: PasswordHasher,
        session_tokens: SessionTokenService,
        session_ttl: timedelta,
    ) -> None:
        self._users = users
        self._sessions = sessions
        self._password_hasher = password_hasher
        self._session_tokens = session_tokens
        self._session_ttl = session_ttl

    def execute(self, command: RegisterUserCommand) -> AuthenticatedUserResult:
        email = Email(command.email)
        if self._users.get_by_email(email) is not None:
            raise EmailAlreadyRegisteredError("Email address is already registered.")

        now = datetime.now(UTC)
        user = User.register(
            email=email,
            password_hash=self._password_hasher.hash(command.password),
            now=now,
        )
        token = self._session_tokens.new_token()
        expires_at = now + self._session_ttl
        session = Session(
            id=str(uuid.uuid4()),
            user_id=user.id,
            token_hash=self._session_tokens.token_hash(token),
            created_at=now,
            expires_at=expires_at,
        )

        self._users.add(user)
        self._sessions.add(session)

        return AuthenticatedUserResult(
            user=UserDto.from_user(user),
            session_token=token,
            session_expires_at=expires_at,
        )
