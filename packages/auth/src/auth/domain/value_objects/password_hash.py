from dataclasses import dataclass

from auth.domain.exceptions import InvalidPasswordHashError


@dataclass(frozen=True, slots=True)
class PasswordHash:
    """Argon2id password hash persisted for a local user."""

    value: str

    def __post_init__(self) -> None:
        if not self.value.startswith("$argon2id$"):
            raise InvalidPasswordHashError("Password hash must use Argon2id.")

    def __str__(self) -> str:
        return self.value
