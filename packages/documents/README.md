# Memovi Documents

Document ingestion and document lifecycle domain boundary. This package owns the
normalized document model that every connector and ingestion workflow uses.

## Current scope

This package owns document ingestion, lifecycle, and asynchronous processing:

- Domain aggregates: `Document`, `DocumentVersion`, and `ProcessingJob`
- Value objects: `DocumentId`, `DocumentName`, `MimeType`, and `SourceType`
- Processing lifecycle enum and domain events
- Application commands and queries for document registration and processing
- In-memory processing queue and background worker for local development
- SQLAlchemy repositories, object storage, and document upload API

The import package is `documents` because the package boundary is already clear
from `packages/documents`.

## Layout

- `domain` — business model, invariants, repository interfaces, and events
- `application` — use cases, DTOs, queue ports, workers, and application exceptions
- `infrastructure` — persistence, processors, object storage, queue implementations
- `api` — upload endpoint, schemas, dependencies, and router

## Out of scope for this foundation

- OCR, chunking, and embeddings
- Distributed queues and external worker runtimes
