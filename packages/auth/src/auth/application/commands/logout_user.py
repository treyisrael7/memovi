from collections.abc import Sequence
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
        self.execute_many((session_token,))

    def execute_many(self, session_tokens: Sequence[str]) -> None:
        seen: set[str] = set()
        now = datetime.now(UTC)
        for session_token in session_tokens:
            if not session_token or session_token in seen:
                continue
            seen.add(session_token)
            session = self._sessions.get_by_token_hash(
                self._session_tokens.token_hash(session_token)
            )
            if session is None:
                continue
            self._sessions.save(session.revoke(now))
