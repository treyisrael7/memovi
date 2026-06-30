from typing import Protocol

from auth.domain.entities import Session


class SessionRepository(Protocol):
    """Persistence contract for browser-backed local sessions."""

    def get_by_token_hash(self, token_hash: str) -> Session | None:
        raise NotImplementedError

    def add(self, session: Session) -> None:
        raise NotImplementedError

    def save(self, session: Session) -> None:
        raise NotImplementedError
