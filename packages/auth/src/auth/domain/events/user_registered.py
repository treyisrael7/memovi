from dataclasses import dataclass
from datetime import datetime

from auth.domain.value_objects import UserId


@dataclass(frozen=True, slots=True)
class UserRegistered:
    """Domain fact emitted after a user registration completes."""

    user_id: UserId
    occurred_at: datetime
