from dataclasses import dataclass
from datetime import datetime

from auth.domain.entities import Session, User


@dataclass(frozen=True, slots=True)
class AuthenticatedPrincipal:
    """Authenticated user and session resolved from a durable session cookie."""

    user_id: str
    session_id: str
    email: str
    created_at: datetime

    @classmethod
    def from_user_and_session(cls, user: User, session: Session) -> AuthenticatedPrincipal:
        return cls(
            user_id=user.id.value,
            session_id=session.id,
            email=user.email.value,
            created_at=user.created_at,
        )
