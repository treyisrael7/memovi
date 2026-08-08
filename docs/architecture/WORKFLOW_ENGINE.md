# Workflow Engine

# Purpose

This document describes Memovi's Workflow Engine durability model: how workflow
definitions and execution history are persisted, versioned, recovered across
restarts, and observed in production.

# Scope

It covers:

* Durable workflow definitions (library)
* Durable workflow execution history and status
* Startup recovery without duplicate execution
* Versioning of definitions
* Observability metrics

It does **not** redesign planner, capability execution, loops, conditionals, or
background schedulers. Those remain owned by
[`WORKFLOW_AUTOMATION.md`](WORKFLOW_AUTOMATION.md),
[`CAPABILITY_PLANNER.md`](CAPABILITY_PLANNER.md), and
[`CAPABILITY_EXECUTION.md`](CAPABILITY_EXECUTION.md).

# Relationship to WORKFLOW_AUTOMATION.md

[`WORKFLOW_AUTOMATION.md`](WORKFLOW_AUTOMATION.md) defines the orchestration
model (validate → plan → execute → record). This document focuses on the
persistence and recovery layer behind `WorkflowLibrary` and
`WorkflowHistoryStore`.

Package path: `packages/automation/src/memovi_automation/`

# Persistence Model

## Workflow definitions

Table: `automation_workflow_definitions`

| Field | Notes |
| --- | --- |
| `workflow_id` | Primary key |
| `workspace_id` | Optional workspace scope (`null` for global/built-ins) |
| `name`, `description` | Human-readable metadata |
| `version` | Monotonic integer; incremented on update |
| `steps`, `variables` | JSON payloads matching domain contracts |
| `expected_outputs`, `required_capabilities` | JSON arrays |
| `metadata` | Extensible map (`builtin: true` for seeded starters) |
| `created_at`, `updated_at` | Timestamps |

Adapters:

* `SqlAlchemyWorkflowLibrary` — production / durable
* `InMemoryWorkflowLibrary` — tests and local fallback

Library operations:

* **Create** — insert; fails if id exists
* **Update** — replace body; bumps `version`; built-ins are immutable
* **Delete** — remove; built-ins cannot be deleted
* **Duplicate** — copy under a new id at version `1`
* **List / Get** — restore catalog after restart

Built-in workflows are seeded on startup when missing. Existing customized rows
are never overwritten by seeding.

## Workflow history

Table: `automation_workflow_history`

| Field | Notes |
| --- | --- |
| `instance_id` | Execution id (primary key) |
| `workflow_id`, `workflow_name` | Definition identity at run time |
| `workspace_id`, `user_id` | Ownership / actor |
| `status` | `running` / `completed` / `failed` / `awaiting_approval` / `cancelled` |
| `started_at`, `completed_at`, `duration` | Timing |
| `executed_steps`, `failed_steps` | Step outcome ids |
| `error_details` | Failure messages |
| `executed_capabilities`, `audit_references` | Capability correlation |
| `result_summary` | Compact review payload |
| `full_result` | Full `WorkflowExecutionResult` JSON for detail views |

Adapters:

* `SqlAlchemyWorkflowHistoryStore`
* `InMemoryWorkflowHistoryStore`

The engine checkpoints progress:

1. Persist `running` as soon as an instance starts
2. Upsert after each successful step
3. Persist the terminal status and full result on finish

# Recovery

On API startup (`configure_capability_execution`):

1. Restore the workflow library (seed built-ins if needed)
2. Restore history from `automation_workflow_history`
3. Call `WorkflowEngine.recover_interrupted_workflows()`

Recovery rules:

* Rows with status `running` are marked `failed` with
  `interrupted_by_restart` semantics (`recovered: true` in metadata)
* Rows with status `awaiting_approval` are **left intact** so pending capability
  approvals can continue through the Capability Execution Engine after restart
* Interrupted runs are **not** auto-resumed — this avoids duplicate side effects

# Versioning

* New definitions start at `version = 1`
* Updates increment version (library enforces monotonic growth)
* Duplicates reset to `version = 1` under a new `workflow_id`
* Built-in definitions are immutable (update/delete rejected)

Execution history stores the workflow name/id used for that run; it does not
rewrite historical rows when a definition is later updated.

# History Semantics

History survives application restart and is workspace-scoped for list/get.

Each entry exposes:

* Execution id, workflow id/name, workspace, user
* Status, started/completed timestamps, duration
* Executed steps, failed steps, error details
* Capability audit references
* Result summary suitable for desktop Activity / Workflows history

# Observability

`WorkflowEngine` records metrics via `memovi_observability`:

| Metric | Meaning |
| --- | --- |
| `memovi.workflows.execution.duration_ms` | Run duration |
| `memovi.workflows.execution.completed` | Success count |
| `memovi.workflows.execution.failed` | Failure count |
| `memovi.workflows.execution.cancelled` | Cancellation count |
| `memovi.workflows.execution.awaiting_approval` | Approval waits |
| `memovi.workflows.execution.recovered` | Interrupted runs recovered on startup |

Structured logs (`workflow.execute.*`, `workflow.step.execute`,
`workflow.recover`) remain the primary operational trail.

# HTTP Surface

Existing desktop routes are unchanged in meaning:

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/workflows` | List library |
| `GET` | `/workflows/{id}` | Get definition |
| `POST` | `/workflows/{id}/execute` | Execute |
| `GET` | `/workflows/history` | List history |
| `GET` | `/workflows/history/{instance_id}` | Full result |

Durability-supporting library routes (optional for desktop):

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/workflows` | Create definition |
| `PUT` | `/workflows/{id}` | Update definition |
| `DELETE` | `/workflows/{id}` | Delete definition |
| `POST` | `/workflows/{id}/duplicate` | Duplicate definition |

# Out of Scope

* Auto-resume of remaining steps after approval across a full multi-step instance
* Background / scheduled workflow runners
* Loops, parallel fans, conditionals
* A second workflow runtime

# Related Documents

* [`WORKFLOW_AUTOMATION.md`](WORKFLOW_AUTOMATION.md)
* [`CAPABILITY_EXECUTION.md`](CAPABILITY_EXECUTION.md)
* [`CAPABILITY_PLANNER.md`](CAPABILITY_PLANNER.md)
* [`DESKTOP_CLIENT.md`](DESKTOP_CLIENT.md)
* [`../STATUS.md`](../STATUS.md)
