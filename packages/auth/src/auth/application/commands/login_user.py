import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from auth.application.commands.register_user import AuthenticatedUserResult
from auth.application.dto import UserDto
from auth.application.exceptions import InvalidCredentialsError
from auth.application.ports import PasswordHasher, SessionTokenService
from auth.domain.entities import Session
from auth.domain.repositories import SessionRepository, UserRepository
from auth.domain.value_objects import Email


@dataclass(frozen=True, slots=True)
class LoginUserCommand:
    email: str
    password: str


class LoginUser:
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

    def execute(self, command: LoginUserCommand) -> AuthenticatedUserResult:
        user = self._users.get_by_email(Email(command.email))
        if user is None:
            raise InvalidCredentialsError("Email address or password is incorrect.")

        if not self._password_hasher.verify(user.password_hash, command.password):
            raise InvalidCredentialsError("Email address or password is incorrect.")

        now = datetime.now(UTC)
        token = self._session_tokens.new_token()
        expires_at = now + self._session_ttl
        session = Session(
            id=str(uuid.uuid4()),
            user_id=user.id,
            token_hash=self._session_tokens.token_hash(token),
            created_at=now,
            expires_at=expires_at,
        )
        self._sessions.add(session)

        return AuthenticatedUserResult(
            user=UserDto.from_user(user),
            session_token=token,
            session_expires_at=expires_at,
        )
