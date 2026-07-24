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
* Immutable contracts: `CapabilityMetadata`, `CapabilityPermission`,
  `CapabilityRequest`, `CapabilityResult`, `CapabilityContext`,
  `CapabilityExecutionPolicy`, `CapabilityExecutionRequest/Result/Context`,
  `ExecutionAuditEntry`, `PermissionMode`
* `FilesystemCapability` — first production capability (root-scoped read + write)
* HTTP API under `/capabilities` for discovery, execution, approval, and audit

It does **not** implement git/terminal/browser capabilities, multi-step planning,
background scheduling, or autonomous agents.

## Layout

```text
src/memovi_automation/
├── api/                  # FastAPI capability execution routes
├── application/          # Ports, registry, invoker, execution engine
├── domain/               # Value objects and exceptions
├── filesystem/           # Root-scoped Filesystem Capability (read + write)
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
