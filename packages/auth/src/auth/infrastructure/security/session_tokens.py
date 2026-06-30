import hashlib
import secrets


class SecureSessionTokenService:
    """Issues opaque cookie tokens and stores only stable hashes."""

    def new_token(self) -> str:
        return secrets.token_urlsafe(48)

    def token_hash(self, token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()
