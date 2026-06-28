# Auth Domain Layer

The domain layer owns identity concepts and invariants for authentication and
authorization. It is independent of FastAPI, databases, provider SDKs, and queues.

Current contents are intentionally minimal:

- `entities` defines auth domain entities.
- `events` defines lightweight auth domain facts.
- `repositories` defines persistence interfaces owned by the domain.
- `services` is reserved for domain rules that do not belong to one entity.
- `value_objects` defines immutable auth values.
- `exceptions.py` defines domain-level failure types.
