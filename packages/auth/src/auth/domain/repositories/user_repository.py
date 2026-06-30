from typing import Protocol

from auth.domain.entities import User
from auth.domain.value_objects import Email, UserId


class UserRepository(Protocol):
    """Persistence contract for local identity use cases."""

    def get_by_id(self, user_id: UserId) -> User | None:
        raise NotImplementedError

    def get_by_email(self, email: Email) -> User | None:
        raise NotImplementedError

    def add(self, user: User) -> None:
        raise NotImplementedError
