# Capability Execution Engine

# Purpose

This document describes the Capability Execution Engine: the secure pipeline that
lets Intelligence and clients invoke registered capabilities without calling them
directly.

# Relationship to ARCHITECTURE.md

Capabilities live in `packages/automation`. Intelligence decides **when** an
action may be useful. The execution engine owns **whether** and **how** a single
capability run proceeds under permission policy, validation, and audit.

See also [`CAPABILITY_FRAMEWORK.md`](CAPABILITY_FRAMEWORK.md) for registry and
capability contracts, [`CAPABILITY_PLANNER.md`](CAPABILITY_PLANNER.md) for
plan-then-execute composition, [`FILESYSTEM_CAPABILITY.md`](FILESYSTEM_CAPABILITY.md)
for filesystem, [`TERMINAL_CAPABILITY.md`](TERMINAL_CAPABILITY.md) for terminal
command execution, [`GIT_CAPABILITY.md`](GIT_CAPABILITY.md) for structured
Git operations, and [`BROWSER_CAPABILITY.md`](BROWSER_CAPABILITY.md) for
structured web access.

# Safety Philosophy

1. **No direct capability calls from Intelligence.** Conversation and reasoning
   code submit work to the engine (or an Intelligence-facing port that adapts to
   the engine). They never import concrete capabilities or call
   `Capability.execute`.
2. **Permission before side effects.** Capability-specific modes
   (`always_allow`, `ask_every_time`, `deny`) gate execution before the invoker
   runs.
3. **User control for risky actions.** `ask_every_time` leaves executions in
   `pending_approval` until the user approves or cancels.
4. **Structured, auditable outcomes.** Every transition is recorded. Clients
   render structured status/output/errors rather than raw capability dumps.
5. **Narrow scope.** No autonomous loops, background scheduling, or write
   operations beyond what a registered capability already supports.

# Execution Lifecycle

```text
Conversation / Intelligence / API
            │
            ▼
 CapabilityExecutionRequest
            │
            ▼
 CapabilityExecutionEngine
   ├─ resolve capability (registry)
   ├─ resolve permission mode
   ├─ validate / await approval
   ├─ invoke via CapabilityInvoker
   ├─ normalize CapabilityExecutionResult
   └─ append ExecutionAuditEntry
            │
            ▼
 Structured result → Conversation / Desktop
```

Statuses:

| Status | Queue / UX label | Meaning |
| --- | --- | --- |
| `pending_approval` | Awaiting approval | Waiting for explicit user approval |
| `executing` | Running | Invoker is running the capability |
| `completed` | Completed | Structured success output available |
| `failed` | Failed | Normalized error (deny, unknown, invalid args, capability failure, restart interrupt) |
| `cancelled` | Cancelled | User or host cancelled before/during run |

There is no separate pre-authorization `pending` status: `submit` either returns
`pending_approval`, runs immediately (`executing` → terminal), or fails.

# Persistence Model

Live execution state is durable in `automation_capability_executions`
(`SqlAlchemyExecutionStateStore`). The engine API is unchanged; only the state
backend moved off process-local dicts.

| Concern | Store | Survives restart |
| --- | --- | --- |
| Live results (`get` / `list`) | `ExecutionStateStore` | Yes |
| Pending approval request + auth snapshot | `ExecutionStateStore` | Yes |
| Audit trail | `ExecutionAuditStore` | Yes |
| Permission policies | `PermissionPolicyStore` | Yes |
| Cancellation tokens | Process-local | No (recreated on approve) |

Persisted execution fields include execution id, workspace/user/session ids,
capability, status, permission mode, progress output, timestamps, failure
details, redacted-safe metadata, and (for `pending_approval`) the request
arguments needed to resume after approve. Audit entries continue to redact
secrets/content independently.

# Restart Recovery

On API startup the composition root calls
`CapabilityExecutionEngine.recover_interrupted_executions()`:

1. Rows in `executing` are marked `failed` with
   `interrupted_by_restart` (mid-flight work is not auto-resumed — avoids
   duplicate side effects).
2. Rows in `pending_approval` remain pending with stored request/auth payloads.
3. Completed / failed / cancelled history is preserved and listable.

# Approval Recovery

If the process restarts while an execution is `pending_approval`:

1. Desktop/`GET /capabilities/executions?status=pending_approval` still lists it.
2. `POST .../approve` reloads the pending request from durable state.
3. Policy is re-evaluated at approval time; then the invoker runs normally.

# Observability

Metrics via existing `memovi_observability`:

| Metric | Meaning |
| --- | --- |
| `memovi.capabilities.execution.duration_ms` | Invoke duration |
| `memovi.capabilities.execution.completed` | Completions |
| `memovi.capabilities.execution.failed` | Failures |
| `memovi.capabilities.execution.cancelled` | Cancellations |
| `memovi.capabilities.execution.pending_approval` | New pending approvals |
| `memovi.capabilities.execution.recovered` | Interrupted rows recovered |
| `memovi.capabilities.execution.resume_skipped` | Interrupted executions not resumed |

# Permission Enforcement

Permission modes are **capability-specific**, workspace-scoped, and
**server-owned**. See [`AUTHORIZATION.md`](AUTHORIZATION.md).

| Mode | Behavior |
| --- | --- |
| `always_allow` | Execute immediately after authorization |
| `ask_every_time` | Return `pending_approval`; `approve` continues |
| `deny` | Fail with `permission_denied` without invoking |

Resolution order (Authorization Service):

1. Durable workspace policy store for that capability
2. Engine default (`ask_every_time`)

Clients must not submit `permission_mode` on execution requests. Policy changes
use authenticated `PUT /capabilities/{id}/permission-mode`.

After approval (or always-allow), the engine grants Authorization Service
effective permissions into `CapabilityContext.granted_permissions` for the
invoker/capability check.

# Core Types

| Type | Role |
| --- | --- |
| `CapabilityExecutionEngine` | Pipeline owner: resolve, authorize, invoke, audit |
| `CapabilityExecutionRequest` | Workspace-scoped request with arguments and correlation |
| `AuthenticatedExecutionContext` | Required user/session/workspace/request identity |
| `CapabilityAuthorizationService` | Server-owned membership + policy decisions |
| `CapabilityExecutionResult` | Status, output, duration, errors, metadata |
| `CapabilityExecutionPolicy` | Timeout and cancellability (not client authz) |
| `ExecutionAuditEntry` | Durable audit record with user, operation, redacted args |
| `ExecutionStateStore` | Live execution + pending approval persistence |

`CapabilityInvoker` remains the single-invocation executor. The engine sits
**above** the invoker and is the only supported path for Intelligence.

# Audit Model

Every status transition appends a durable `ExecutionAuditEntry` capturing:

* Timestamp
* User
* Workspace
* Capability id
* Operation (when present)
* Redacted arguments (secrets/tokens redacted)
* Result summary (status, error code/message, has_output)
* Duration
* Optional conversation / correlation ids
* Source (`intelligence`, `api`, …)

Audit history survives process restarts and is listed via
`GET /capabilities/executions/audit` for Activity views and debugging.
Production uses `SqlAlchemyExecutionAuditStore`.

# Intelligence Bridge

Intelligence owns a `CapabilityExecutionPort` with `CapabilityExecutionView`
DTOs. The composition root (`apps/api`) adapts that port to
`CapabilityExecutionEngine`.

Conversation endpoints:

* `POST /conversations/{id}/capability-executions`
* `GET /conversations/{id}/capability-executions`

These call the port only. They do not touch the registry or invoker.

# Desktop Presentation

Desktop Chat polls pending and conversation-scoped executions and renders:

* Pending approval prompts (Approve / Deny)
* Executing / completed / failed / cancelled states
* Structured output for completed runs

Desktop remains presentation-only.

# API Surface

| Endpoint | Role |
| --- | --- |
| `GET /capabilities` | Discover registered capabilities + modes |
| `PUT /capabilities/{id}/permission-mode` | Set Always Allow / Ask / Deny |
| `POST /capabilities/executions` | Submit execution |
| `GET /capabilities/executions` | List executions (optional status filter) |
| `GET /capabilities/executions/{id}` | Get one execution |
| `POST /capabilities/executions/{id}/approve` | Approve pending |
| `POST /capabilities/executions/{id}/cancel` | Cancel pending/in-flight |
| `GET /capabilities/executions/audit` | Audit trail |

# Out of Scope

* Autonomous goal-seeking agent loops
* Background task scheduling
* Conditional/loop workflow runners (plan contracts reserve room; see
  [`CAPABILITY_PLANNER.md`](CAPABILITY_PLANNER.md) for deterministic plan/validate)
* Write operations beyond existing capability support
* Automatic resume of mid-flight `executing` work after crash (marked failed instead)

# Related Documents

* [`CAPABILITY_FRAMEWORK.md`](CAPABILITY_FRAMEWORK.md)
* [`CAPABILITY_PLANNER.md`](CAPABILITY_PLANNER.md)
* [`FILESYSTEM_CAPABILITY.md`](FILESYSTEM_CAPABILITY.md)
* [`intelligence-architecture.md`](intelligence-architecture.md)
* [`DESKTOP_CLIENT.md`](DESKTOP_CLIENT.md)
