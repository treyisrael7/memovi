# Memovi Automation

Capability Framework package. Owns capability abstractions, registry, metadata,
permission declarations, invocation contracts, execution context, and the
Capability Execution Engine.

## Current Scope

This package establishes the architecture for safe, composable capabilities that
Intelligence can discover and invoke:

* `Capability` protocol — provider-agnostic executable units
* `CapabilityRegistry` — explicit registration and metadata discovery
* `CapabilityInvoker` — single-invocation execution with timeout and cancellation
* `CapabilityExecutionEngine` — permission modes, approval, audit, normalized results
* `CapabilityPlanner` / `ExecutionPlanValidator` — deterministic plan build + validate (never executes)
* `PlanExecutionService` — submits validated plan steps only through the engine
* `WorkflowEngine` / `WorkflowValidator` / `WorkflowHistory` — reusable sequential
  workflows with variables, input/output mapping, and execution history
* Immutable contracts: `CapabilityMetadata`, `CapabilityPermission`,
  `CapabilityRequest`, `CapabilityResult`, `CapabilityContext`,
  `CapabilityExecutionPolicy`, `CapabilityExecutionRequest/Result/Context`,
  `ExecutionPlan` / `ExecutionStep` / `ExecutionPlanResult`,
  `WorkflowDefinition` / `WorkflowStep` / `WorkflowExecutionResult`,
  `ExecutionAuditEntry`, `PermissionMode`
* `FilesystemCapability` — root-scoped read + write
* `TerminalCapability` — root-scoped command execution (stdout/stderr/exit/duration)
* `GitCapability` — structured repository ops (status/branch/commit/diff/remote)
* `BrowserCapability` — structured web open/read/search/download
* HTTP API under `/capabilities` for discovery, execution, approval, and audit
* HTTP API under `/workflows` for library, execute, and history

It does **not** implement loops, conditionals, parallel fans, background
scheduling, or autonomous agents. Concrete capabilities are never exposed
directly to the LLM; production runs go through the Capability Execution Engine.
Workflows always plan through the Capability Planner before execution.

## Layout

```text
src/memovi_automation/
├── api/                  # FastAPI capability execution routes
├── application/          # Ports, registry, invoker, execution engine
├── domain/               # Value objects and exceptions
├── filesystem/           # Root-scoped Filesystem Capability (read + write)
├── terminal/             # Root-scoped Terminal Capability
├── git/                  # Structured Git Capability
├── browser/              # Structured Browser Capability
└── infrastructure/       # In-memory policy + audit stores
```

## Relationship to Intelligence Tools

Intelligence `Tool` contracts describe LLM-facing call schemas used during
reasoning. Capabilities describe permissioned environment actions. Intelligence
submits host actions through a composition-root adapter to the execution engine
and never calls capabilities directly.

See:

* [`docs/architecture/CAPABILITY_FRAMEWORK.md`](../../docs/architecture/CAPABILITY_FRAMEWORK.md)
* [`docs/architecture/CAPABILITY_EXECUTION.md`](../../docs/architecture/CAPABILITY_EXECUTION.md)
* [`docs/architecture/FILESYSTEM_CAPABILITY.md`](../../docs/architecture/FILESYSTEM_CAPABILITY.md)
* [`docs/architecture/FILESYSTEM_WRITE.md`](../../docs/architecture/FILESYSTEM_WRITE.md)
* [`docs/architecture/TERMINAL_CAPABILITY.md`](../../docs/architecture/TERMINAL_CAPABILITY.md)
* [`docs/architecture/GIT_CAPABILITY.md`](../../docs/architecture/GIT_CAPABILITY.md)
* [`docs/architecture/BROWSER_CAPABILITY.md`](../../docs/architecture/BROWSER_CAPABILITY.md)
* [`docs/architecture/CAPABILITY_PLANNER.md`](../../docs/architecture/CAPABILITY_PLANNER.md)
* [`docs/architecture/WORKFLOW_AUTOMATION.md`](../../docs/architecture/WORKFLOW_AUTOMATION.md)
