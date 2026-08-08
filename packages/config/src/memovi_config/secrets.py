"""Secret value wrapper that redacts credentials in logs and diagnostics."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SecretValue:
    """Opaque secret that never reveals its value via ``str`` or ``repr``.

    Call ``get_secret_value()`` only at the boundary that needs the raw secret
    (for example constructing a database URL or provider client). Do not put
    secret values into exception messages, logs, or diagnostics.
    """

    _value: str

    def get_secret_value(self) -> str:
        return self._value

    def __bool__(self) -> bool:
        return bool(self._value)

    def __repr__(self) -> str:
        return "SecretValue('***')"

    def __str__(self) -> str:
        return "***"
