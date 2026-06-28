from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Email:
    """Email address value object for future identity workflows."""

    value: str
