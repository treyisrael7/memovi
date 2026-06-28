from dataclasses import dataclass
from datetime import datetime

from auth.domain.value_objects import UserId


@dataclass(frozen=True, slots=True)
class UserLoggedIn:
    """Domain fact emitted after a user login completes."""

    user_id: UserId
    occurred_at: datetime
