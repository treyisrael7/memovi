from datetime import UTC, datetime

from auth.application.dto import UserDto
from auth.application.exceptions import UnauthenticatedError
from auth.application.ports import SessionTokenService
from auth.domain.repositories import SessionRepository, UserRepository


class GetCurrentUser:
    def __init__(
        self,
        *,
        users: UserRepository,
        sessions: SessionRepository,
        session_tokens: SessionTokenService,
    ) -> None:
        self._users = users
        self._sessions = sessions
        self._session_tokens = session_tokens

    def execute(self, session_token: str | None) -> UserDto:
        if not session_token:
            raise UnauthenticatedError("Authentication is required.")

        session = self._sessions.get_by_token_hash(self._session_tokens.token_hash(session_token))
        if session is None or not session.is_active(datetime.now(UTC)):
            raise UnauthenticatedError("Authentication is required.")

        user = self._users.get_by_id(session.user_id)
        if user is None:
            raise UnauthenticatedError("Authentication is required.")

        return UserDto.from_user(user)
