# Memovi Automation

Capability Framework package. Owns capability abstractions, registry, metadata,
permission declarations, invocation contracts, and execution context.

## Current Scope

This package establishes the architecture for safe, composable capabilities that
Intelligence can discover and invoke:

* `Capability` protocol — provider-agnostic executable units
* `CapabilityRegistry` — explicit registration and metadata discovery
* `CapabilityInvoker` — single-invocation execution with timeout and cancellation
* Immutable contracts: `CapabilityMetadata`, `CapabilityPermission`,
  `CapabilityRequest`, `CapabilityResult`, `CapabilityContext`,
  `CapabilityExecutionPolicy`
* `FilesystemCapability` — first production capability (read-only, root-scoped)

It does **not** implement filesystem writes, git/terminal/browser capabilities,
approval UI, multi-step planning, or autonomous agents.

## Layout

```text
src/memovi_automation/
├── application/          # Ports, registry, invoker
├── domain/               # Value objects and exceptions
├── filesystem/           # Read-only Filesystem Capability
└── infrastructure/       # Reserved notes for future adapters
```

## Relationship to Intelligence Tools

Intelligence `Tool` contracts describe LLM-facing call schemas used during
reasoning. Capabilities describe permissioned environment actions. Tools may
later bridge into capabilities; they are not the same abstraction.

See [`docs/architecture/CAPABILITY_FRAMEWORK.md`](../../docs/architecture/CAPABILITY_FRAMEWORK.md).
