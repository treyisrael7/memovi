# Documents Domain Layer

The domain layer owns normalized document concepts and ingestion invariants. It is
independent of FastAPI, databases, object storage, provider SDKs, and queues.

Current contents:

- `entities` defines document aggregates and related entities.
- `enums` defines processing lifecycle states.
- `events` defines lightweight document domain facts.
- `repositories` defines persistence interfaces owned by the domain.
- `services` is reserved for domain rules that do not belong to one entity.
- `value_objects` defines immutable document values.
- `exceptions.py` defines domain-level failure types.
