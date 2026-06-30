from dataclasses import dataclass
from datetime import datetime

from auth.domain.entities import User


@dataclass(frozen=True, slots=True)
class UserDto:
    id: str
    email: str
    created_at: datetime

    @classmethod
    def from_user(cls, user: User) -> UserDto:
        return cls(
            id=user.id.value,
            email=user.email.value,
            created_at=user.created_at,
        )
