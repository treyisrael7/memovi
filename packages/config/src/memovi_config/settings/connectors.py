"""Connector process settings."""

from __future__ import annotations

from dataclasses import dataclass

from memovi_config.env import Environ


@dataclass(frozen=True, slots=True)
class ConnectorsSettings:
    """Process-level connector settings.

    Per-connector credentials remain environment-variable references on each
    connector's ``AuthCredentialRef``; they are not duplicated here.
    """

    @classmethod
    def from_environ(cls, environ: Environ) -> ConnectorsSettings:
        del environ
        return cls()
