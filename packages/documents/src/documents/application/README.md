# Documents Application Layer

The application layer coordinates document ingestion use cases. It depends on the
domain layer and expresses commands, queries, and DTOs without transport or
persistence details.

Current contents:

- `commands` defines write use cases for document registration and processing.
- `queries` defines read use cases for document retrieval.
- `dto` defines application-facing document projections.
- `exceptions.py` defines use-case failure types.
- `services` is reserved for cross-cutting application orchestration.
