import re
from dataclasses import dataclass

from auth.domain.exceptions import InvalidEmailError

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@dataclass(frozen=True, slots=True)
class Email:
    """Normalized email address used as a local Memovi identity."""

    value: str

    def __post_init__(self) -> None:
        normalized = self.value.strip().lower()
        if not EMAIL_PATTERN.fullmatch(normalized):
            raise InvalidEmailError("Email address is invalid.")

        object.__setattr__(self, "value", normalized)

    def __str__(self) -> str:
        return self.value
