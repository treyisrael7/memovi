from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class UserId:
    """Stable identifier for a Memovi identity."""

    value: str
