# Document Processing Pipeline

# Purpose

This document describes how Memovi runs asynchronous document ingestion after
upload or reprocess. It complements
[`knowledge-processing-pipeline.md`](knowledge-processing-pipeline.md), which
owns the full knowledge lifecycle.

# Scope

Durable processing queue lifecycle, worker claim/execution, retries, failure
handling, restart recovery, and status exposure on document APIs.

# Relationship to Architecture

Documents owns ingestion artifacts, processing jobs, and the processing worker.
The API composition root wires a durable `ProcessingJobQueue` implementation and
starts the in-process worker. Downstream Memory and Search continue to react to
processing completion events — this milestone does not redesign that pipeline.

# Pipeline Stages (unchanged)

```text
Upload / Reprocess
        │
        ▼
Persist document + version + PENDING job  (Postgres + object storage)
        │
        ▼
Enqueue (metadata + wake) / poll PENDING jobs
        │
        ▼
Worker claims job atomically
        │
        ▼
Extract → Normalize → COMPLETED | FAILED
        │
        ▼
Domain events → Memory / Search
```

Processing stages remain:

| Stage | Status value | Queue view |
| --- | --- | --- |
| Waiting | `pending` | Pending |
| Extracting text | `extracting` | Running |
| Normalizing text | `normalizing` | Running |
| Success | `completed` | Completed |
| Permanent failure | `failed` | Failed |
| Superseded / stopped | `cancelled` | Cancelled |

# Durable Queue

## Source of truth

`documents_processing_jobs` is the durable queue. There is no separate broker for
V1. Process-local `InMemoryProcessingJobQueue` remains available for unit and
integration tests.

Production wiring uses `SqlAlchemyProcessingJobQueue`.

## Job fields

| Field | Purpose |
| --- | --- |
| `id` | Job ID |
| `document_id` / `document_version_id` | Target artifact |
| `workspace_id` | Workspace context (denormalized) |
| `status` | Stage / terminal state |
| `attempt` | Retry count (starts at 1) |
| `request_id` | Optional originating request correlation |
| `failure_reason` | Error details for failed/cancelled jobs |
| `created_at` / `updated_at` | Audit timestamps |
| `started_at` / `completed_at` | Run timing |
| `available_at` | When the job becomes claimable |
| `claimed_at` | Lease marker preventing duplicate execution |

## Queue lifecycle

1. **Create** — ingest/reprocess inserts a `pending` job in the same DB
   transaction as the document version.
2. **Enqueue** — after commit, the API session hook calls `queue.enqueue(...)`
   to persist attempt/request/workspace metadata and wake the worker. If the
   process dies before enqueue, the pending row remains claimable by polling.
3. **Claim** — `dequeue` selects the oldest eligible pending job and sets
   `claimed_at` under row lock (`FOR UPDATE SKIP LOCKED` on PostgreSQL).
4. **Run** — `ProcessDocument` transitions `pending → extracting → normalizing →
   completed|failed` and sets `started_at` / `completed_at`.
5. **Terminal** — completed, failed, or cancelled jobs are never reclaimed.

# Retries

Transient failures (`ConnectionError`, `TimeoutError`, `OSError`) raise
`TransientDocumentProcessingError`.

Worker behavior:

1. Roll back the processing transaction.
2. If `attempt < max_retries` (default 3): reset the job to `pending`, clear
   claim timestamps, re-enqueue with `attempt + 1`.
3. Otherwise: mark the job `failed` with the error reason and publish
   `ProcessingFailed`.

Retry count is durable on the job row, so retries survive restarts.

# Failure handling

| Failure class | Result |
| --- | --- |
| Unsupported / corrupt content | Immediate `failed` (non-retryable) |
| Transient storage / I/O | Retry up to `max_retries` |
| Exhausted retries | `failed` with last error |
| Reprocess while prior job active | Prior non-terminal job → `cancelled` |

# Recovery after restart

On first `dequeue` after worker start, the durable queue:

1. Resets interrupted `extracting` / `normalizing` jobs back to `pending`.
2. Clears stale `claimed_at` values on pending jobs (abandoned leases).

Pending jobs that were never claimed are picked up automatically. No manual
replay step is required.

# Duplicate processing prevention

- Atomic claim via row locks + `claimed_at`
- `ProcessDocument` only starts jobs that are still `pending`
- Reprocess cancels the previous active job for that document before creating a
  new pending job

# API status exposure

Desktop and other clients continue to use existing document endpoints:

- `POST /documents` / `POST /documents/{id}/reprocess` return `processing_job_id`
  and `processing_status`
- `GET /documents` / `GET /documents/{id}` include processing fields, including
  optional `processing_attempt`, `processing_started_at`, and
  `processing_completed_at`

No parallel processing-status API is introduced.

# User-visible processing lifecycle

Desktop maps the Documents job statuses above into product language. It does
**not** invent a second backend status model.

| Backend `processing_status` | User-visible label | UI copy |
| --- | --- | --- |
| *(client upload in progress)* | Uploading | Upload progress (real transfer percent only) |
| `pending` | Received | Memovi received this document. It is waiting to be processed. |
| `extracting` | Processing | Memovi is processing this document. |
| `normalizing` | Processing | Memovi is processing this document. |
| `completed` | Ready | This is ready to search. |
| `failed` | Failed | Processing failed. Try processing again. |
| `cancelled` | Cancelled | Processing stopped. Try processing again. |

The desktop does **not** invent later pipeline stages (knowledge materialization,
search indexing, embeddings) as Documents statuses. Those continue after
`completed` but are not distinguishable from `GET /documents`.

## Search readiness (presentation)

Search readiness follows the same Documents `processing_status` field. The
document list is the source of truth.

| Condition | Search cue |
| --- | --- |
| Job in flight (`pending` / `extracting` / `normalizing`) | Not ready — still processing |
| `completed` | Ready to search |
| `failed` | Processing failed |
| `cancelled` | Not ready |

Search uses these cues so documents still processing are not silently ignored:
empty results and banners explain that in-flight documents are excluded until
processing finishes.

## Retry behavior (user-facing)

| Action | Behavior |
| --- | --- |
| Automatic retry | Worker retries transient I/O up to `max_retries` (see Retries) |
| Manual retry / reprocess | `POST /documents/{id}/reprocess` cancels any non-terminal job and enqueues a new `pending` job |
| Desktop | Failed / cancelled surfaces emphasize **Retry processing**; other states keep **Reprocess** |

# Indexing lifecycle (downstream, unchanged)

Documents completion is not the end of the knowledge path. Existing event
handlers continue to run after `ProcessingCompleted`:

```text
Documents COMPLETED
        │
        ▼
Memory materializes knowledge (chunks)
        │
        ▼
Search indexes the knowledge item
        │
        ▼
Embeddings enrich search documents (async)
```

Desktop presents Documents `completed` as **Ready to search**. Downstream Memory
materialization, search indexing, and embedding generation remain backend
concerns and are not shown as extra Documents stages. Embedding generation
is not a separate Documents status.

# Observability

Metrics recorded through `memovi_observability` (existing recorder):

| Metric | Meaning |
| --- | --- |
| `memovi.documents.processing.queue_depth` | Pending job count |
| `memovi.documents.processing.claimed` | Successful claims |
| `memovi.documents.processing.duration_ms` | Per-job processing duration |
| `memovi.documents.processing.completed` | Successful completions |
| `memovi.documents.processing.failed` | Permanent failures |
| `memovi.documents.processing.retries` | Scheduled retries |
| `memovi.documents.processing.throughput` | Completed jobs (throughput counter) |
| `memovi.documents.processing.recovered` | Jobs recovered after restart |

Structured worker logs continue to carry request/workspace context when present
on the queued job.

# Related documents

- [`knowledge-processing-pipeline.md`](knowledge-processing-pipeline.md)
- [`DESKTOP_CLIENT.md`](DESKTOP_CLIENT.md)
- [`../testing/DESKTOP_TESTING.md`](../testing/DESKTOP_TESTING.md)
- [`storage-architecture.md`](storage-architecture.md)
- [`event-architecture.md`](event-architecture.md)
- [`observability.md`](observability.md)
- [`CONFIGURATION.md`](CONFIGURATION.md)
