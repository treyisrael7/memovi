# Documents Infrastructure Layer

The infrastructure layer will provide persistence and external integrations for
the documents domain. This commit scaffolds persistence models only.

Current contents:

- `persistence` defines SQLAlchemy records for future repository implementations.
- `repositories` is reserved for SQLAlchemy repository adapters.

Repository implementations are intentionally omitted until storage is introduced.
