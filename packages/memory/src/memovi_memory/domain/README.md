# Memory Domain Layer

The domain layer owns durable knowledge concepts and invariants. It is independent
of FastAPI, databases, document ingestion internals, search providers, and AI SDKs.

Current contents:

- `entities` defines knowledge aggregates and related entities.
- `events` defines lightweight memory domain facts.
- `repositories` defines persistence interfaces owned by the domain.
- `services` defines deterministic domain behavior such as chunk generation.
- `value_objects` defines immutable memory values.
- `exceptions.py` defines domain-level failure types.
