# Capability Planner

# Purpose

This document defines Memovi's Capability Planner: the component that lets
Intelligence create structured, deterministic execution plans before any
capability runs.

# Scope

It covers the planning lifecycle, plan validation, separation from execution,
core plan contracts, Intelligence integration, and future workflow compatibility.

It does **not** define autonomous agents, conditional branching, loops, scheduled
workflows, or background orchestration graphs. Those remain future Automation
features that should build on this planner.

# Relationship to ARCHITECTURE.md

[`../ARCHITECTURE.md`](../ARCHITECTURE.md),
[`CAPABILITY_FRAMEWORK.md`](CAPABILITY_FRAMEWORK.md), and
[`CAPABILITY_EXECUTION.md`](CAPABILITY_EXECUTION.md) establish that environment
actions are permissioned capabilities invoked only through the Capability
Execution Engine. This document adds the planning layer that decides **which**
capabilities to use and **in what order** — without performing those actions.

# Architecture

```text
Conversation
    ↓
Intelligence
    ↓
Capability Planner
    ↓
Execution Plan
    ↓
Capability Execution Engine
    ↓
Capabilities
    ↓
Results
    ↓
Conversation
```

Key rules:

* The planner never calls `Capability.execute`.
* The planner never calls `CapabilityInvoker.invoke`.
* The planner never calls `CapabilityExecutionEngine.submit`.
* Plan execution is a separate service that submits steps only through the engine.
* Desktop never builds or executes plans against host APIs directly.

Package path: `packages/automation/src/memovi_automation/application/services/`

Core types live in `memovi_automation.domain.value_objects.execution_plan`.

# Core Components

| Component | Responsibility |
| --- | --- |
| `CapabilityPlanner` | Build ordered plans from step drafts; validate before return |
| `ExecutionPlan` | Deterministic plan: id, workspace, goal, steps, capabilities, deps |
| `ExecutionStep` | One planned capability operation + arguments + dependencies |
| `ExecutionDependency` | Edge onto a prior step (`success` / `completed` / `always`) |
| `ExecutionPlanValidator` | Capability/operation/argument/dependency validation |
| `ExecutionPlanResult` | Aggregate outcome after engine submission |
| `PlanExecutionService` | Submit validated steps through the Capability Execution Engine |

# Separation of Ownership

| Layer | Owns |
| --- | --- |
| Planner | Capability selection, ordering, dependency resolution, plan validation |
| Execution Engine | Permissions, execution, progress, audit, error handling |
| Capabilities | Business logic for a single operation |

# Planning Lifecycle

1. **Intent** — Intelligence decides a high-level goal
   (for example: search → open page → extract content).
2. **Draft** — Intelligence supplies ordered step drafts
   (`capability_id`, `operation`, `arguments`, optional `dependencies`).
3. **Build** — `CapabilityPlanner.create_plan` constructs an `ExecutionPlan`.
4. **Validate** — `ExecutionPlanValidator` checks:
   * capability exists in the registry
   * operation is supported by that capability
   * arguments satisfy the capability parameter schema
   * dependency graph is valid (known ids, no cycles, deps precede dependents)
5. **Return** — validated plan is returned to Intelligence. No side effects.

# Execution Lifecycle

1. **Hand-off** — Intelligence (or an API client) asks `PlanExecutionService`
   to execute a plan (or uses the Intelligence planner port `execute_plan`).
2. **Re-validate** — the plan is validated again immediately before submission.
3. **Submit steps** — each step becomes a `CapabilityExecutionRequest` with
   `plan_id` / `step_id` metadata and is submitted to the engine.
4. **Authorize** — the engine applies Allow / Ask Every Time / Deny.
5. **Pause or continue** — pending approval stops the plan with
   `awaiting_approval`; failures stop with `failed`; success continues.
6. **Aggregate** — `ExecutionPlanResult` summarizes step outcomes.

The planner is not involved in permission prompts, progress streaming, or audit
persistence beyond producing metadata the engine can record.

# Execution Plan Shape

Each plan contains:

* Plan ID
* Workspace
* Goal
* Ordered steps
* Required capabilities
* Dependencies (derived edges)
* Estimated execution count

Plans are immutable. For identical planning inputs (workspace, goal, steps,
conversation/correlation ids, metadata), the planner derives a stable
content-based `plan_id` so repeated requests produce the same plan structure
and identity. `created_at` remains a wall-clock timestamp.

# Execution Step Shape

Each step contains:

* Step ID
* Capability
* Operation
* Arguments
* Dependencies
* Expected result (descriptive; not enforced at runtime yet)

No execution occurs during planning.

# Intelligence Integration

Intelligence depends on `CapabilityPlannerPort` only:

* `create_plan` — validate and return an `ExecutionPlanView`
* `validate_plan` — re-validate a plan draft
* `execute_plan` — validate then submit through `PlanExecutionService`

Composition root adapter: `apps/api/src/api/capability_planner_integration.py`

Conversation HTTP:

* `POST /conversations/{id}/capability-plans` — create/validate plan
* `POST /conversations/{id}/capability-plans/execute` — execute via engine

# Future Compatibility

Plan contracts reserve room for future Automation features without implementing
them now:

* Conditional execution (`ExecutionDependency.kind` and step metadata)
* Loops / retries (plan metadata + future step kinds)
* User approval checkpoints (engine Ask Every Time already pauses plan execution)
* Background workflows (async workers submitting plans)
* Scheduled workflows (scheduler producing plans)

Do not grow the planner into an agent runtime. Multi-step autonomy belongs to a
later Automation phase built on these contracts.

# Related Documents

* [`CAPABILITY_FRAMEWORK.md`](CAPABILITY_FRAMEWORK.md)
* [`CAPABILITY_EXECUTION.md`](CAPABILITY_EXECUTION.md)
* [`BROWSER_CAPABILITY.md`](BROWSER_CAPABILITY.md)
* [`../ARCHITECTURE.md`](../ARCHITECTURE.md)
* [`../STATUS.md`](../STATUS.md)
* [`../ROADMAP.md`](../ROADMAP.md)
