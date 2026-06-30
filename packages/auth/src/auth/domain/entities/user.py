from dataclasses import dataclass
from datetime import UTC, datetime

from auth.domain.value_objects import Email, PasswordHash, UserId


@dataclass(frozen=True, slots=True)
class User:
    """Local identity that owns knowledge in a self-hosted Memovi instance."""

    id: UserId
    email: Email
    password_hash: PasswordHash
    created_at: datetime

    @classmethod
    def register(
        cls,
        *,
        email: Email,
        password_hash: PasswordHash,
        now: datetime | None = None,
    ) -> User:
        return cls(
            id=UserId.new(),
            email=email,
            password_hash=password_hash,
            created_at=now or datetime.now(UTC),
        )
