from typing import Protocol

from auth.domain.value_objects import PasswordHash


class PasswordHasher(Protocol):
    """Hashes and verifies local user passwords."""

    def hash(self, password: str) -> PasswordHash:
        raise NotImplementedError

    def verify(self, password_hash: PasswordHash, password: str) -> bool:
        raise NotImplementedError


class SessionTokenService(Protocol):
    """Creates and fingerprints opaque browser session tokens."""

    def new_token(self) -> str:
        raise NotImplementedError

    def token_hash(self, token: str) -> str:
        raise NotImplementedError
