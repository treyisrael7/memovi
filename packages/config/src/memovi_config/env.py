"""Typed helpers for reading process environment variables."""

from __future__ import annotations

from collections.abc import Mapping
from urllib.parse import urlparse

from memovi_config.exceptions import ConfigurationError
from memovi_config.secrets import SecretValue

Environ = Mapping[str, str]


def raw_get(environ: Environ, name: str) -> str | None:
    """Return the raw environment value, or ``None`` when unset."""
    if name not in environ:
        return None
    return environ[name]


def get_str(
    environ: Environ,
    name: str,
    *,
    default: str | None = None,
    required: bool = False,
    allow_blank: bool = False,
) -> str | None:
    """Read a string setting.

    When ``required`` is true and the variable is missing or blank, raise
    ``ConfigurationError``. Blank values are rejected unless ``allow_blank``.
    """
    value = raw_get(environ, name)
    if value is None:
        if required and default is None:
            raise ConfigurationError(f"{name} is required.")
        return default
    stripped = value.strip()
    if not stripped and not allow_blank:
        if required:
            raise ConfigurationError(f"{name} cannot be blank.")
        if default is not None:
            return default
        raise ConfigurationError(f"{name} cannot be blank.")
    return stripped


def get_int(
    environ: Environ,
    name: str,
    *,
    default: int | None = None,
    required: bool = False,
    minimum: int | None = None,
    maximum: int | None = None,
) -> int:
    """Read an integer setting with optional bounds."""
    value = raw_get(environ, name)
    if value is None or not value.strip():
        if required and default is None:
            raise ConfigurationError(f"{name} is required.")
        if default is None:
            raise ConfigurationError(f"{name} is required.")
        return default
    try:
        parsed = int(value.strip())
    except ValueError as exc:
        raise ConfigurationError(f"{name} must be an integer.") from exc
    if minimum is not None and parsed < minimum:
        raise ConfigurationError(f"{name} must be at least {minimum}.")
    if maximum is not None and parsed > maximum:
        raise ConfigurationError(f"{name} must be at most {maximum}.")
    return parsed


def get_float(
    environ: Environ,
    name: str,
    *,
    default: float | None = None,
    required: bool = False,
    minimum: float | None = None,
) -> float:
    """Read a floating-point setting with optional lower bound."""
    value = raw_get(environ, name)
    if value is None or not value.strip():
        if required and default is None:
            raise ConfigurationError(f"{name} is required.")
        if default is None:
            raise ConfigurationError(f"{name} is required.")
        return default
    try:
        parsed = float(value.strip())
    except ValueError as exc:
        raise ConfigurationError(f"{name} must be a number.") from exc
    if minimum is not None and parsed < minimum:
        raise ConfigurationError(f"{name} must be at least {minimum}.")
    return parsed


def get_secret(
    environ: Environ,
    name: str,
    *,
    default: str | None = None,
    required: bool = False,
) -> SecretValue | None:
    """Read a secret. Never embed the value in raised errors."""
    value = raw_get(environ, name)
    if value is None:
        if required and default is None:
            raise ConfigurationError(f"{name} is required.")
        if default is None:
            return None
        return SecretValue(default)
    stripped = value.strip()
    if not stripped:
        if required:
            raise ConfigurationError(f"{name} cannot be blank.")
        if default is None:
            return None
        return SecretValue(default)
    return SecretValue(stripped)


def require_http_url(name: str, value: str) -> str:
    """Validate that ``value`` is an absolute http(s) URL."""
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ConfigurationError(
            f"{name} must be an absolute http(s) URL.",
        )
    return value


def require_database_url(name: str, value: str) -> str:
    """Validate that ``value`` looks like a SQLAlchemy database URL."""
    stripped = value.strip()
    if not stripped:
        raise ConfigurationError(f"{name} cannot be blank.")
    parsed = urlparse(stripped)
    scheme = (parsed.scheme or "").lower()
    if scheme.startswith("sqlite"):
        return stripped
    if "postgresql" in scheme or scheme in {"postgres", "postgresql"}:
        if not parsed.netloc and not parsed.path:
            raise ConfigurationError(f"{name} is not a valid database URL.")
        return stripped
    raise ConfigurationError(
        f"{name} must be a postgresql or sqlite SQLAlchemy URL.",
    )
