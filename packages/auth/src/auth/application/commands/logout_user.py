from datetime import UTC, datetime

from auth.application.ports import SessionTokenService
from auth.domain.repositories import SessionRepository


class LogoutUser:
    def __init__(
        self,
        *,
        sessions: SessionRepository,
        session_tokens: SessionTokenService,
    ) -> None:
        self._sessions = sessions
        self._session_tokens = session_tokens

    def execute(self, session_token: str | None) -> None:
        if not session_token:
            return

        session = self._sessions.get_by_token_hash(self._session_tokens.token_hash(session_token))
        if session is None:
            return

        self._sessions.save(session.revoke(datetime.now(UTC)))
