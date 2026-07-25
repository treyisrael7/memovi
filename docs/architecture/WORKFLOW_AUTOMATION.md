# Workflow Automation

# Purpose

This document defines Memovi's Workflow Automation Framework: reusable,
declarative sequences of capability steps that coordinate complex tasks without
embedding business logic in Desktop or Intelligence.

# Scope

It covers workflow definitions, variables, validation, sequential execution,
structured results, history, planner integration, permissions, and desktop
presentation.

It does **not** define loops, parallel execution, conditionals, background
schedulers, or autonomous agents. Those remain future Automation milestones.

# Relationship to ARCHITECTURE.md

[`../ARCHITECTURE.md`](../ARCHITECTURE.md),
[`CAPABILITY_FRAMEWORK.md`](CAPABILITY_FRAMEWORK.md),
[`CAPABILITY_EXECUTION.md`](CAPABILITY_EXECUTION.md), and
[`CAPABILITY_PLANNER.md`](CAPABILITY_PLANNER.md) establish permissioned
capabilities, the execution engine, and plan-then-execute composition.

This document adds reusable workflow orchestration **on top of** the planner and
execution engine. Workflows never call `Capability.execute` or
`CapabilityInvoker.invoke` directly.

# Architecture

```text
Conversation / Desktop
    ↓
Intelligence (optional) / Workflow Engine
    ↓
Capability Planner
    ↓
Execution Plan (per step)
    ↓
Capability Execution Engine
    ↓
Capabilities
    ↓
Results + Workflow History
    ↓
Conversation / Desktop
```

Key rules:

* Every workflow step is materialized through `CapabilityPlanner.create_plan`.
* Every plan step is submitted only through `PlanExecutionService` →
  `CapabilityExecutionEngine`.
* Workflows inherit permission modes of contained capabilities (Allow / Ask /
  Deny).
* Desktop owns presentation only (library, run, progress, history).

Package path: `packages/automation/src/memovi_automation/`

# Core Components

| Component | Responsibility |
| --- | --- |
| `WorkflowDefinition` | Human-readable reusable workflow: id, name, steps, variables, outputs |
| `WorkflowStep` | Capability step with input/output mapping |
| `WorkflowVariable` | Declared typed input (string/path/number/boolean) |
| `WorkflowContext` | Runtime variables + prior step outputs |
| `WorkflowInstance` | One run of a definition |
| `WorkflowExecutionResult` | Structured status, steps, outputs, errors, audit refs |
| `WorkflowValidator` | Definition + variable validation before execution |
| `WorkflowEngine` | Orchestrates validate → plan → execute → history |
| `WorkflowHistory` / store | Prior execution summaries for review |
| `WorkflowLibrary` | Catalog of reusable definitions (built-ins + registered) |

# Workflow Lifecycle

1. **Define** — Author a `WorkflowDefinition` (built-in library or register).
2. **Discover** — Clients list workflows via `GET /workflows`.
3. **Bind** — Supply runtime variables; `WorkflowValidator` coerces and checks
   required values.
4. **Validate** — Definition checked against the capability registry
   (capabilities exist, operations supported, references resolve).
5. **Execute** — `WorkflowEngine.execute` runs steps sequentially.
6. **Record** — `WorkflowHistory` stores name, timestamp, workspace, duration,
   result summary, and executed capabilities.
7. **Review** — Desktop or API clients inspect history and full results.

# Execution Model

For each step, in order:

1. Resolve `input_mapping` with variable substitution
   (`${var}` and `${steps.<step_id>.<path>}`).
2. Create a validated `ExecutionPlan` via the Capability Planner.
3. Submit the plan through `PlanExecutionService` (engine permissions + audit).
4. On success, apply `output_mapping` into `WorkflowContext`.
5. Stop on `failed`, `cancelled`, or `awaiting_approval`.

`materialize_plan` can preview a full plan when all inputs resolve from
variables alone (no prior-step references).

# Variables

Declared on the definition and validated before execution.

Examples: `source_folder`, `destination_folder`, `repository`, `search_query`.

Unsupported for this milestone: loops over variable collections, dynamic step
graphs.

# Results

Each run returns:

* Workflow status (`completed` / `failed` / `awaiting_approval` / `cancelled`)
* Completed and failed step ids
* Per-step results (capability, status, output, errors, plan/execution ids)
* Duration
* Bound outputs
* Errors
* Audit references (capability execution ids)

# History

Stored per workspace:

* Workflow name
* Execution timestamp
* Workspace
* Duration
* Result summary
* Executed capabilities
* Audit references

Default store is process-local (`InMemoryWorkflowHistoryStore`). Durable
persistence remains future work.

# Planner Integration

Workflows do not bypass the planner:

* Step arguments are planned through `CapabilityPlanner`.
* Argument schema validation occurs in the planner validator before invoke.
* Plan metadata includes `workflow_id` and `workflow_instance_id` for audit
  correlation.

# Permissions

Each workflow inherits the permission modes of its contained capabilities.
Ask Every Time prompts occur at the Capability Execution Engine boundary.
Workflow code never auto-approves.

# Desktop

The Workflows page (`apps/desktop`) provides:

* Workflow Library
* Run Workflow (variable form)
* Execution Progress
* Execution History

All calls go through the platform HTTP API (`/workflows`).

# HTTP Surface

Built-in library includes `list-directory`, `run-command` (Terminal),
`summarize-git-status`, `inspect-then-list`, and `download-and-verify`
(Browser download → Filesystem exists, with `${steps.download.destination}`
mapping). `GET /workflows` only returns definitions whose required capabilities
are registered.

# Observability

`WorkflowEngine.execute` emits structured operations via `memovi_observability`:

* `workflow.execute.start` / `workflow.execute.finish` — include `workflow_id`
* `workflow.step.execute` — one log per step with `workflow_id`, `step_id`,
  `capability_id`, `plan_id`, `execution_id`

Ambient HTTP `request_id` / `correlation_id` from `RequestContext` are stamped
onto every log line and copied into plan/step metadata so they propagate through
Capability Execution Engine audit entries.

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/workflows` | List library (capabilities available) |
| `GET` | `/workflows/{id}` | Get definition |
| `POST` | `/workflows/{id}/execute` | Run with variables |
| `GET` | `/workflows/history` | List history |
| `GET` | `/workflows/history/{instance_id}` | Full result |

# Out of Scope

* Loops, parallel fans, conditionals
* Background / scheduled workflow runners
* Resume-after-approval of remaining steps in one instance
* Durable cross-process history
* LLM-authored workflow graphs

# Future Compatibility

Reserved extensions:

* Conditional / loop step kinds on workflow definitions
* Durable history and approval resume
* Intelligence-selected workflows from conversation intent
* Background Activity page integration

# Related Documents

* [`CAPABILITY_FRAMEWORK.md`](CAPABILITY_FRAMEWORK.md)
* [`CAPABILITY_EXECUTION.md`](CAPABILITY_EXECUTION.md)
* [`CAPABILITY_PLANNER.md`](CAPABILITY_PLANNER.md)
* [`DESKTOP_CLIENT.md`](DESKTOP_CLIENT.md)
* [`../STATUS.md`](../STATUS.md)
