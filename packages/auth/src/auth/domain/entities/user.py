from dataclasses import dataclass

from auth.domain.value_objects import Email, UserId


@dataclass(frozen=True, slots=True)
class User:
    """Identity aggregate placeholder for future authentication behavior."""

    id: UserId
    email: Email
