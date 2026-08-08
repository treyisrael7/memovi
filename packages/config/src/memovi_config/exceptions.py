"""Configuration package exceptions."""

from __future__ import annotations


class ConfigurationError(ValueError):
    """Raised when environment configuration is missing or invalid.

    Messages must never include secret values. Prefer naming the environment
    variable and describing the constraint.
    """
