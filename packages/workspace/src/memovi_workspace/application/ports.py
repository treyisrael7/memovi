from typing import Protocol


class UserDirectoryPort(Protocol):
    """Lookup registered users without coupling Workspace to Auth infrastructure."""

    def find_user_id_by_email(self, email: str) -> str | None:
        raise NotImplementedError

    def find_email_by_user_id(self, user_id: str) -> str | None:
        raise NotImplementedError
