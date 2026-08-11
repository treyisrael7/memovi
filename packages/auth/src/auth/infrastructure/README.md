# Auth Infrastructure Layer

The infrastructure layer implements external concerns for the auth domain while
keeping those details out of domain and application code.

Contents:

- `persistence` — SQLAlchemy ORM models for users and sessions.
- `repositories` — SQLAlchemy repository implementations.
- `security` — Argon2id password hashing and session token adapters.
