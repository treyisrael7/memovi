# Auth Domain Layer

The domain layer owns identity concepts and invariants for authentication and
authorization. It is independent of FastAPI, databases, provider SDKs, and queues.

Contents:

- `entities` — auth domain entities.
- `events` — reserved package for durable auth domain facts (none published yet).
- `repositories` — persistence interfaces owned by the domain.
- `value_objects` — immutable auth values.
- `exceptions.py` — domain-level failure types.
