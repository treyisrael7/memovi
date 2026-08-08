"""Capability root process settings."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from memovi_config.env import Environ, get_float, get_int, get_str
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


def parse_csv_set(environ: Environ, env_name: str) -> frozenset[str] | None:
    """Parse a comma-separated set.

    Returns ``None`` when unset (callers keep capability defaults). Returns an
    empty frozenset when set to a blank/whitespace-only value after the key is
    present with explicit empty intent via a single empty token is not used —
    blank means use defaults (``None``).
    """
    if env_name not in environ:
        return None
    raw = environ[env_name]
    if raw is None:
        return None
    stripped = raw.strip()
    if not stripped:
        # Explicit empty list: disable default entries when callers pass through.
        return frozenset()
    return frozenset(part.strip().lower() for part in stripped.split(",") if part.strip())


def parse_pattern_list(environ: Environ, env_name: str) -> tuple[str, ...] | None:
    """Parse semicolon-separated regex patterns. ``None`` when unset."""
    if env_name not in environ:
        return None
    raw = environ[env_name]
    if raw is None:
        return None
    stripped = raw.strip()
    if not stripped:
        return ()
    return tuple(part.strip() for part in stripped.split(";") if part.strip())


def parse_bool(environ: Environ, env_name: str, *, default: bool) -> bool:
    raw = get_str(environ, env_name, default=None)
    if raw is None:
        return default
    lowered = raw.strip().lower()
    if lowered in {"1", "true", "yes", "on"}:
        return True
    if lowered in {"0", "false", "no", "off"}:
        return False
    raise ConfigurationError(f"{env_name} must be a boolean (true/false).")


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
    terminal_allowed_executables: frozenset[str] | None = None
    terminal_denied_executables: frozenset[str] | None = None
    terminal_confirm_executables: frozenset[str] | None = None
    terminal_denied_argument_patterns: tuple[str, ...] | None = None
    terminal_default_timeout_seconds: float = 30.0
    terminal_max_timeout_seconds: float = 300.0
    terminal_max_stdout_bytes: int = 1_048_576
    terminal_max_stderr_bytes: int = 1_048_576
    terminal_prefer_argv: bool = True
    terminal_allow_shell: bool = True

    @classmethod
    def from_environ(cls, environ: Environ) -> CapabilitiesSettings:
        default_timeout = get_float(
            environ,
            "MEMOVI_TERMINAL_DEFAULT_TIMEOUT_SECONDS",
            default=30.0,
            minimum=0.1,
        )
        max_timeout = get_float(
            environ,
            "MEMOVI_TERMINAL_MAX_TIMEOUT_SECONDS",
            default=300.0,
            minimum=0.1,
        )
        if default_timeout > max_timeout:
            raise ConfigurationError(
                "MEMOVI_TERMINAL_DEFAULT_TIMEOUT_SECONDS cannot exceed "
                "MEMOVI_TERMINAL_MAX_TIMEOUT_SECONDS.",
            )
        return cls(
            filesystem_roots=parse_capability_roots(environ, "MEMOVI_FILESYSTEM_ROOTS"),
            terminal_roots=parse_capability_roots(environ, "MEMOVI_TERMINAL_ROOTS"),
            git_roots=parse_capability_roots(environ, "MEMOVI_GIT_ROOTS"),
            browser_download_roots=parse_capability_roots(
                environ,
                "MEMOVI_BROWSER_DOWNLOAD_ROOTS",
            ),
            terminal_allowed_executables=parse_csv_set(
                environ,
                "MEMOVI_TERMINAL_ALLOWED_EXECUTABLES",
            ),
            terminal_denied_executables=parse_csv_set(
                environ,
                "MEMOVI_TERMINAL_DENIED_EXECUTABLES",
            ),
            terminal_confirm_executables=parse_csv_set(
                environ,
                "MEMOVI_TERMINAL_CONFIRM_EXECUTABLES",
            ),
            terminal_denied_argument_patterns=parse_pattern_list(
                environ,
                "MEMOVI_TERMINAL_DENIED_ARGUMENT_PATTERNS",
            ),
            terminal_default_timeout_seconds=default_timeout,
            terminal_max_timeout_seconds=max_timeout,
            terminal_max_stdout_bytes=get_int(
                environ,
                "MEMOVI_TERMINAL_MAX_STDOUT_BYTES",
                default=1_048_576,
                minimum=1,
            ),
            terminal_max_stderr_bytes=get_int(
                environ,
                "MEMOVI_TERMINAL_MAX_STDERR_BYTES",
                default=1_048_576,
                minimum=1,
            ),
            terminal_prefer_argv=parse_bool(
                environ,
                "MEMOVI_TERMINAL_PREFER_ARGV",
                default=True,
            ),
            terminal_allow_shell=parse_bool(
                environ,
                "MEMOVI_TERMINAL_ALLOW_SHELL",
                default=True,
            ),
        )
