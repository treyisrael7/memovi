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
capability contracts, and [`FILESYSTEM_CAPABILITY.md`](FILESYSTEM_CAPABILITY.md)
for the first concrete capability.

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

| Status | Meaning |
| --- | --- |
| `pending_approval` | Waiting for explicit user approval |
| `executing` | Invoker is running the capability |
| `completed` | Structured success output available |
| `failed` | Normalized error (deny, unknown, invalid args, capability failure) |
| `cancelled` | User or host cancelled before/during run |

# Permission Enforcement

Permission modes are **capability-specific** and workspace-scoped:

| Mode | Behavior |
| --- | --- |
| `always_allow` | Execute immediately after resolution |
| `ask_every_time` | Return `pending_approval`; `approve` continues |
| `deny` | Fail with `permission_denied` without invoking |

Resolution order:

1. Optional `permission_mode` on the submitted `CapabilityExecutionPolicy`
2. Workspace policy store for that capability
3. Engine default (`ask_every_time`)

Future desktop settings will manage these policies. This milestone exposes the
API (`PUT /capabilities/{id}/permission-mode`) and engine store.

After approval (or always-allow), the engine grants the capability's declared
metadata permissions into `CapabilityContext.granted_permissions` for the
invoker/capability check.

# Core Types

| Type | Role |
| --- | --- |
| `CapabilityExecutionEngine` | Pipeline owner: resolve, authorize, invoke, audit |
| `CapabilityExecutionRequest` | Workspace-scoped request with arguments and correlation |
| `CapabilityExecutionContext` | Cancellation, conversation, source metadata |
| `CapabilityExecutionResult` | Status, output, duration, errors, metadata |
| `CapabilityExecutionPolicy` | Timeout, cancellability, optional permission mode |
| `ExecutionAuditEntry` | Immutable audit record with redacted arguments |

`CapabilityInvoker` remains the single-invocation executor. The engine sits
**above** the invoker and is the only supported path for Intelligence.

# Audit Model

Every status transition appends an `ExecutionAuditEntry` capturing:

* Timestamp
* Workspace
* Capability id
* Redacted arguments (secrets/tokens redacted)
* Result summary (status, error code/message, has_output)
* Duration
* Optional conversation / correlation ids
* Source (`intelligence`, `api`, …)

Audit history is listed via `GET /capabilities/executions/audit` for future
Activity views and debugging. The default store is in-memory; durable storage
can replace the port later without changing the engine contract.

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

* Autonomous multi-step workflows
* Background task scheduling
* Graph/agent planners
* Write operations beyond existing capability support
* Durable audit database (port exists; in-memory default)

# Related Documents

* [`CAPABILITY_FRAMEWORK.md`](CAPABILITY_FRAMEWORK.md)
* [`FILESYSTEM_CAPABILITY.md`](FILESYSTEM_CAPABILITY.md)
* [`intelligence-architecture.md`](intelligence-architecture.md)
* [`DESKTOP_CLIENT.md`](DESKTOP_CLIENT.md)
