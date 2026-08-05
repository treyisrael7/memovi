# Auth Domain Layer

The domain layer owns identity concepts and invariants for authentication and
authorization. It is independent of FastAPI, databases, provider SDKs, and queues.

Contents:

- `entities` — auth domain entities.
- `events` — lightweight auth domain facts.
- `repositories` — persistence interfaces owned by the domain.
- `services` — domain rules that do not belong to one entity.
- `value_objects` — immutable auth values.
- `exceptions.py` — domain-level failure types.
