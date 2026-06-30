from dataclasses import dataclass
from datetime import datetime

from auth.domain.exceptions import InvalidSessionError
from auth.domain.value_objects import UserId


@dataclass(frozen=True, slots=True)
class Session:
    """Persistent local browser session for a Memovi user."""

    id: str
    user_id: UserId
    token_hash: str
    created_at: datetime
    expires_at: datetime
    revoked_at: datetime | None = None

    def __post_init__(self) -> None:
        if not self.id:
            raise InvalidSessionError("Session ID is required.")
        if not self.token_hash:
            raise InvalidSessionError("Session token hash is required.")
        if self.expires_at <= self.created_at:
            raise InvalidSessionError("Session expiry must be after creation.")

    def is_active(self, now: datetime) -> bool:
        return self.revoked_at is None and self.expires_at > now

    def revoke(self, now: datetime) -> Session:
        return Session(
            id=self.id,
            user_id=self.user_id,
            token_hash=self.token_hash,
            created_at=self.created_at,
            expires_at=self.expires_at,
            revoked_at=now,
        )
