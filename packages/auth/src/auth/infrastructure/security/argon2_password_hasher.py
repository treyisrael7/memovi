from argon2 import PasswordHasher as Argon2PasswordHasher
from argon2.exceptions import VerificationError, VerifyMismatchError

from auth.domain.value_objects import PasswordHash


class Argon2idPasswordHasher:
    """Argon2id password adapter for local Memovi accounts."""

    def __init__(self) -> None:
        self._hasher = Argon2PasswordHasher()

    def hash(self, password: str) -> PasswordHash:
        return PasswordHash(self._hasher.hash(password))

    def verify(self, password_hash: PasswordHash, password: str) -> bool:
        try:
            return self._hasher.verify(password_hash.value, password)
        except VerifyMismatchError, VerificationError:
            return False
