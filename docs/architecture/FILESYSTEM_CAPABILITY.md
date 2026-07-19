# Filesystem Capability

# Purpose

This document defines Memovi's first production Capability: read-only filesystem
access implemented on the Capability Framework.

# Scope

It covers responsibilities, the safety model, permissions, operation surface,
result contracts, and extension points for future write operations. It does not
cover automation orchestration, approval UI, recursive walks, file watching, or
desktop-specific integration.

# Relationship to ARCHITECTURE.md

[`../ARCHITECTURE.md`](../ARCHITECTURE.md) and
[`CAPABILITY_FRAMEWORK.md`](CAPABILITY_FRAMEWORK.md) establish that environment
actions belong to Automation capabilities. This document describes the reference
Filesystem Capability in `memovi_automation.filesystem`.

# Responsibilities

The Filesystem Capability owns safe, synchronous, explicit filesystem reads when
invoked through the Capability Framework.

It supports:

* `read_file` — read text file contents
* `read_directory` — non-recursive directory listing with entry metadata
* `list_directory` — non-recursive entry names
* `exists` — existence / type probe
* `get_metadata` — size, type, and modification time

It does **not** own:

* File writes, deletes, moves, or renames
* Recursive tree walks
* File watching
* HTTP, FastAPI, UI, or desktop code
* Automation planning or multi-step workflows

Capability id: `filesystem`

Package path: `packages/automation/src/memovi_automation/filesystem/`

# Integration with the Capability Framework

The capability implements the `Capability` protocol and must be registered on a
`CapabilityRegistry`:

```python
from pathlib import Path

from memovi_automation import (
    CapabilityInvoker,
    CapabilityRegistry,
    FilesystemCapabilityConfig,
    register_filesystem_capability,
)

registry = CapabilityRegistry()
register_filesystem_capability(
    registry,
    FilesystemCapabilityConfig.from_roots([Path("/allowed/root")]),
)
invoker = CapabilityInvoker(registry=registry)
```

Discovery uses `registry.list()` / `registry.metadata("filesystem")`.
Execution uses `CapabilityInvoker.invoke(...)` so callers receive a structured
`CapabilityResult`. Direct OS access outside this capability is out of scope for
platform filesystem work.

# Safety Model

## Allowed roots

Access is restricted to configured root directories
(`FilesystemCapabilityConfig.allowed_roots`). Roots are normalized at
construction and must exist as directories.

## Path normalization and traversal

Every path argument is:

1. Validated as a non-empty string without null bytes
2. Normalized with `Path.resolve`
3. Checked to remain within at least one allowed root

Relative paths are resolved against allowed roots. Absolute paths are accepted
only when they resolve under an allowed root. Path traversal and symlink escapes
that leave allowed roots fail with `invalid_path`.

## Synchronous, explicit invocation

Operations run only when invoked. There is no background watching, no recursive
descent, and no implicit follow-up I/O beyond the requested operation.

## Read size limit

`read_file` enforces `max_read_bytes` (default 1 MiB) and returns
`file_too_large` when exceeded.

# Permission Model

| Permission | Role |
| --- | --- |
| `filesystem.read` | Required for all current read operations |
| `filesystem.write` | Reserved for future write operations |

The capability metadata currently declares `filesystem.read`.

At execution time:

* Read operations require `filesystem.read` in `CapabilityContext.granted_permissions`
* Reserved write operation names require `filesystem.write`, then return
  `unsupported_operation` until write milestones land

This keeps read/write permissions separate while allowing write ops to be added
without redesigning routing or registration.

# Result Model

Callers always observe a `CapabilityResult` from `CapabilityInvoker`.

Success payloads include an `operation` field and operation-specific data
(`content`, `entries`, `exists`, metadata fields, and similar).

Structured failure codes include:

| Code | Meaning |
| --- | --- |
| `permission_denied` | Required filesystem permission not granted |
| `file_not_found` | Target path does not exist |
| `invalid_path` | Blank/null/escaped/outside-root path |
| `unsupported_operation` | Unknown or not-yet-implemented operation |
| `not_a_file` | File operation used on a non-file |
| `not_a_directory` | Directory operation used on a non-directory |
| `not_text_file` | `read_file` could not decode text |
| `file_too_large` | File exceeds configured read limit |

Invoker metadata (argument count, timeout, cancellability) remains available on
successful and failed invocations where applicable.

# Extension Points

Future milestones can extend this capability without replacing the framework:

1. **Write operations** — add handlers for names already reserved in
   `WRITE_OPERATIONS` (`write_file`, `delete_path`, `move_path`, `rename_path`),
   declare `filesystem.write` in metadata, and keep per-operation permission
   checks.
2. **Config** — add write-specific limits (max write bytes, allow-delete flags)
   to `FilesystemCapabilityConfig` without changing read defaults.
3. **Roots** — composition roots inject allowed directories; desktop or API hosts
   decide which roots to expose.
4. **Additional read ops** — extend `READ_OPERATIONS` carefully; avoid recursive
   or watch semantics unless a later milestone explicitly adds them.

Do not invent a parallel filesystem API outside the registry.

# Key Decisions

* Filesystem is a Capability, not Automation and not an agent tool loop.
* Read-only first; write permissions are modeled but not implemented.
* Safety is root-scoped path normalization, not caller trust.
* Permission enforcement uses `CapabilityContext.granted_permissions`.
* HTTP/UI/desktop concerns stay outside this package module.

# Related Documents

* [`CAPABILITY_FRAMEWORK.md`](CAPABILITY_FRAMEWORK.md)
* [`../ARCHITECTURE.md`](../ARCHITECTURE.md)
* [`domains.md`](domains.md)
* [`../STATUS.md`](../STATUS.md)
* [`../ROADMAP.md`](../ROADMAP.md)
