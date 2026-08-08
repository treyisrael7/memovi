"""Capability root process settings."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from memovi_config.env import Environ, get_str
from memovi_config.exceptions import ConfigurationError


def parse_capability_roots(environ: Environ, env_name: str) -> tuple[Path, ...] | None:
    """Parse ``os.pathsep``-separated capability roots.

    Returns ``None`` when the variable is unset or blank (callers apply
    runtime fallbacks). When set, every entry must exist and be a directory.
    """
    raw = get_str(environ, env_name, default=None)
    if raw is None:
        return None
    parts = [part.strip() for part in raw.split(os.pathsep) if part.strip()]
    if not parts:
        raise ConfigurationError(f"{env_name} is set but contains no paths.")
    roots: list[Path] = []
    for part in parts:
        path = Path(part)
        if not path.exists():
            raise ConfigurationError(f"{env_name} path does not exist: {part}")
        if not path.is_dir():
            raise ConfigurationError(f"{env_name} path is not a directory: {part}")
        roots.append(path.resolve())
    return tuple(roots)


@dataclass(frozen=True, slots=True)
class CapabilitiesSettings:
    """Typed filesystem / capability root configuration.

    When a root env var is unset, the corresponding field is ``None`` and the
    API composition root applies its historical fallback (temp directory or
    shared filesystem roots).
    """

    filesystem_roots: tuple[Path, ...] | None = None
    terminal_roots: tuple[Path, ...] | None = None
    git_roots: tuple[Path, ...] | None = None
    browser_download_roots: tuple[Path, ...] | None = None

    @classmethod
    def from_environ(cls, environ: Environ) -> CapabilitiesSettings:
        return cls(
            filesystem_roots=parse_capability_roots(environ, "MEMOVI_FILESYSTEM_ROOTS"),
            terminal_roots=parse_capability_roots(environ, "MEMOVI_TERMINAL_ROOTS"),
            git_roots=parse_capability_roots(environ, "MEMOVI_GIT_ROOTS"),
            browser_download_roots=parse_capability_roots(
                environ,
                "MEMOVI_BROWSER_DOWNLOAD_ROOTS",
            ),
        )
