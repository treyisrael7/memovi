# Memovi Documents

Document ingestion and document lifecycle domain boundary. This package owns the
normalized document model that every connector and ingestion workflow uses.

## Current scope

This package establishes the document domain foundation:

- Domain aggregates: `Document`, `DocumentVersion`, and `ProcessingJob`
- Value objects: `DocumentId`, `DocumentName`, `MimeType`, and `SourceType`
- Processing lifecycle enum and domain events
- Application commands and queries for document registration and processing
- Persistence and API scaffolds without storage or endpoint implementations

The import package is `documents` because the package boundary is already clear
from `packages/documents`.

## Layout

- `domain` — business model, invariants, repository interfaces, and events
- `application` — use cases, DTOs, and application exceptions
- `infrastructure` — persistence model scaffolds (repositories not implemented)
- `api` — placeholder schemas, dependencies, and router

## Out of scope for this foundation

- File uploads and object storage
- OCR, chunking, embeddings, and background workers
- SQLAlchemy repository implementations and database migrations
