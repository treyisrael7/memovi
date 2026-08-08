"""Desktop integration process settings."""

from __future__ import annotations

from dataclasses import dataclass

from memovi_config.env import Environ, get_str, require_http_url
from memovi_config.exceptions import ConfigurationError

DEFAULT_API_BASE = "http://127.0.0.1:8000"


@dataclass(frozen=True, slots=True)
class DesktopSettings:
    """Server-side awareness of the desktop client's API base URL.

    The desktop Vite build reads ``VITE_MEMOVI_API_BASE`` separately. Scripts and
    local tooling may use ``MEMOVI_API_BASE`` with the same default.
    """

    api_base: str = DEFAULT_API_BASE

    def __post_init__(self) -> None:
        api_base = self.api_base.strip().rstrip("/")
        if not api_base:
            raise ConfigurationError("MEMOVI_API_BASE cannot be blank.")
        require_http_url("MEMOVI_API_BASE", api_base)
        object.__setattr__(self, "api_base", api_base)

    @classmethod
    def from_environ(cls, environ: Environ) -> DesktopSettings:
        return cls(
            api_base=get_str(environ, "MEMOVI_API_BASE", default=DEFAULT_API_BASE)
            or DEFAULT_API_BASE,
        )
