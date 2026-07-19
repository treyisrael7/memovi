# Capability Framework

# Purpose

This document defines Memovi's Capability Framework: the architecture for safe,
composable, permissioned actions that Intelligence can discover and invoke.

# Scope

It covers capability abstractions, registry discovery, permission metadata,
execution contracts, safety boundaries, relationship to Intelligence tools, and
the future plugin path. It does not describe concrete filesystem, git, terminal,
or browser implementations, approval UI, or multi-step automation orchestration.

# Relationship to ARCHITECTURE.md

[`../ARCHITECTURE.md`](../ARCHITECTURE.md) identifies Intelligence as a consumer
of knowledge and notes tool orchestration inside reasoning. This document defines
the separate Capability Framework in `packages/automation` that owns environment
actions and permission metadata. Capabilities strengthen the knowledge platform
without becoming an agent runtime.

# Why Capabilities Exist

Capabilities represent things Memovi can do in the user's environment.

Examples of future concrete capabilities:

* Read and write files
* Search directories
* Execute terminal commands
* Access Git repositories
* Read clipboard contents
* Send notifications

Capabilities exist so those actions are:

* Explicit and discoverable
* Declared with required permissions
* Invoked through a stable contract
* Independent of any LLM provider
* Isolated from application internals

Without a capability boundary, environment access tends to scatter across clients,
providers, and ad-hoc helpers. The framework keeps that surface composable and
auditable before Automation and plugins arrive.

# This Is Not an Agent Framework

The Capability Framework is intentionally narrow.

It does **not** provide:

* Autonomous execution loops
* Multi-step planning
* Goal decomposition
* Provider-specific tool calling
* Desktop UI or approval workflows
* Retries or orchestration graphs

Intelligence decides **when** a capability should be considered.

Capabilities decide **how** a single unit of work is performed.

Automation (a later phase) will compose capabilities with approval and provenance.
Agents remain out of scope until the platform can expose explicit, permissioned,
auditable actions.

# Package Ownership

`packages/automation` (`memovi-automation`) owns:

* Capability abstractions
* Capability registry
* Capability metadata
* Invocation interfaces
* Execution context
* Permission model (declarative)
* Result contracts

It does not own durable knowledge, search indexes, conversation memory, or UI.

# Core Interfaces

| Type | Role |
| --- | --- |
| `Capability` | Protocol for a discoverable, executable unit of work |
| `CapabilityRegistry` | Explicit registration, lookup, and metadata discovery |
| `CapabilityInvoker` | Validates arguments and performs a single invocation |
| `CapabilityMetadata` | Stable id, description, parameters, required permissions |
| `CapabilityPermission` | Dotted permission name such as `filesystem.read` |
| `CapabilityRequest` | Invocation identity, arguments, optional execution policy |
| `CapabilityResult` | Success/failure outcome with structured error and metadata |
| `CapabilityContext` | Workspace, cancellation, granted permissions, correlation |
| `CapabilityExecutionPolicy` | Timeout and cancellability constraints |

Capabilities self-register by exposing `metadata()` and being passed to
`CapabilityRegistry.register(...)` from the composition root or a registrar.
There is no reflection and no global registry singleton.

# Discovery

Intelligence discovers capabilities through the registry:

1. Composition root constructs a `CapabilityRegistry`
2. Concrete capabilities are registered explicitly (dependency injection)
3. Callers list metadata via `registry.list()`
4. Callers inspect permissions via `registry.permissions(capability_id)`
5. Callers invoke through `CapabilityInvoker.invoke(request, context)`

Discovery returns metadata only. Registration never executes a capability.

# Permissions

Capabilities declare required permissions as metadata.

Well-known examples:

* `filesystem.read`
* `filesystem.write`
* `terminal.execute`
* `git.read`
* `git.write`
* `browser.read`
* `clipboard.read`
* `clipboard.write`
* `notifications.send`

`CapabilityContext.granted_permissions` supports inspection for future approval
flows. This milestone does not implement user consent UI or enforcement policy
beyond the declarative model.

# Execution Contract

`CapabilityInvoker` supports:

* Success with structured output
* Failure with `CapabilityError` (`code`, `message`, `details`)
* Cooperative cancellation through `CancellationToken`
* Timeouts via `CapabilityExecutionPolicy.timeout_seconds`
* Execution metadata (argument count, timeout, cancellability)

It does not retry, schedule, or chain capabilities.

Unknown capability ids return a `CapabilityResult` with
`CapabilityError(code="unknown_capability", ...)`. Invalid argument schemas raise
domain errors. Execution failures, timeouts, and cancellations also return
`CapabilityResult` values so callers can reason over outcomes without treating
every failure as an unhandled exception.

# Safety Boundaries

Capability implementations must not access application internals directly.

Allowed:

* `CapabilityRequest` arguments
* `CapabilityContext` (workspace id, cancellation, granted permissions, correlation metadata)
* Future host ports attached through context or constructor injection of narrow interfaces

Forbidden:

* Importing FastAPI, HTTP routers, or UI frameworks
* Reaching into Documents, Memory, Search, or Intelligence internals
* Global mutable registries
* Provider-specific SDKs inside the capability contract itself

Concrete adapters may use OS or provider libraries inside infrastructure modules,
but the public capability boundary remains provider-agnostic.

# Relationship to Intelligence Tools

Intelligence already has a `Tool` / `ToolRegistry` / `ToolExecutor` framework for
LLM-facing call schemas during reasoning.

| Concern | Intelligence `Tool` | Automation `Capability` |
| --- | --- | --- |
| Primary consumer | Reasoning / prompt orchestration | Environment actions |
| Provider coupling | Avoided, but tool calling is AI-adjacent | Fully provider-agnostic |
| Permissions | Not modeled | First-class metadata |
| Product examples | Echo / future LLM tools | Filesystem, Git, Terminal, Browser |

A later integration may bridge Tools to Capabilities so an Intelligence tool call
resolves to a permissioned capability invocation. That bridge must not collapse
the two abstractions: tools describe model-callable shapes; capabilities describe
safe host actions.

# Extension Example

```python
from memovi_automation import (
    FILESYSTEM_READ,
    CapabilityContext,
    CapabilityInvoker,
    CapabilityMetadata,
    CapabilityParameter,
    CapabilityRegistry,
    CapabilityRequest,
)
from memovi_shared import WorkspaceId


class ReadTextFileCapability:
    def metadata(self) -> CapabilityMetadata:
        return CapabilityMetadata(
            id="filesystem.read_text",
            description="Read a UTF-8 text file from the local filesystem.",
            permissions=(FILESYSTEM_READ,),
            parameters=(
                CapabilityParameter(
                    name="path",
                    type="string",
                    description="Absolute or workspace-relative file path.",
                ),
            ),
        )

    def execute(self, request: CapabilityRequest, context: CapabilityContext) -> object:
        context.check_cancelled()
        # Future: perform I/O through a host filesystem port on context.
        path = str(request.arguments["path"])
        return {"path": path, "content": ""}


registry = CapabilityRegistry()
registry.register(ReadTextFileCapability())
invoker = CapabilityInvoker(registry=registry)

result = invoker.invoke(
    CapabilityRequest.create(
        capability_id="filesystem.read_text",
        arguments={"path": "README.md"},
    ),
    CapabilityContext.create(workspace_id=WorkspaceId.default()),
)
```

No concrete product capability ships in this milestone. The example above is an
extension sketch for future adapters under
`packages/automation/src/memovi_automation/infrastructure/`.

# Future Plugin Architecture

The registry and metadata contracts are the foundation for plugins:

1. A plugin package implements one or more `Capability` types
2. The composition root loads enabled plugins and registers them
3. Intelligence discovers plugin metadata the same way as built-in capabilities
4. Permissions remain declarative until Automation adds approval and audit
5. Plugins cannot bypass Memory, ownership, or knowledge pipeline boundaries

Plugin loading, sandboxing, and marketplace distribution are future work. They
should extend this framework rather than invent a parallel execution stack.

# Future Roadmap

| Stage | Outcome |
| --- | --- |
| Now | Capability Framework contracts, registry, invoker, tests, docs |
| Next | Concrete capabilities: Filesystem, Git, Terminal, Browser, Clipboard, Notifications |
| Then | Permission enforcement and user approval UX (desktop-first) |
| Later | Automation composition, provenance, background jobs |
| Eventually | Plugin packaging and third-party capability distribution |

# Key Decisions

* Capabilities are not agents and do not plan multi-step work.
* Registration is explicit via dependency injection; no reflection or globals.
* Permissions are metadata first; approval UI comes later.
* Capabilities interact with the host only through `CapabilityContext`.
* Intelligence Tools and Automation Capabilities remain distinct abstractions.
* Concrete product capabilities are intentionally absent in this foundation.

# Related Documents

* [`../ARCHITECTURE.md`](../ARCHITECTURE.md)
* [`intelligence-architecture.md`](intelligence-architecture.md)
* [`domains.md`](domains.md)
* [`module-architecture.md`](module-architecture.md)
* [`../ROADMAP.md`](../ROADMAP.md)
* [`../STATUS.md`](../STATUS.md)
* [`../PRODUCT_VISION.md`](../PRODUCT_VISION.md)
