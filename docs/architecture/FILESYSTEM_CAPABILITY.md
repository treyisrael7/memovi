# Filesystem Capability

# Purpose

This document defines Memovi's first production Capability: root-scoped
filesystem access implemented on the Capability Framework.

# Scope

It covers responsibilities, the safety model, permissions, the read operation
surface, and result contracts. Write operations are documented in
[`FILESYSTEM_WRITE.md`](FILESYSTEM_WRITE.md).

# Relationship to ARCHITECTURE.md

[`../ARCHITECTURE.md`](../ARCHITECTURE.md) and
[`CAPABILITY_FRAMEWORK.md`](CAPABILITY_FRAMEWORK.md) establish that environment
actions belong to Automation capabilities. This document describes the reference
Filesystem Capability in `memovi_automation.filesystem`.

# Responsibilities

The Filesystem Capability owns safe, synchronous, explicit filesystem reads and
writes when invoked through the Capability Framework / Execution Engine.

Read operations:

* `read_file` — read text file contents
* `read_directory` — non-recursive directory listing with entry metadata
* `list_directory` — non-recursive entry names
* `exists` — existence / type probe
* `get_metadata` — size, type, and modification time

Write operations (see [`FILESYSTEM_WRITE.md`](FILESYSTEM_WRITE.md)):

* create, replace, append, rename, copy, move, delete (file and directory)

It does **not** own:

* Recursive tree walks or file watching
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

Production callers submit through the Capability Execution Engine so permission
modes, approval, and audit apply. Direct OS access outside this capability is
out of scope for platform filesystem work.

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
| `filesystem.read` | Required for all read operations |
| `filesystem.create` | Create file / directory |
| `filesystem.modify` | Replace / append / write_file |
| `filesystem.move` | Rename / copy / move |
| `filesystem.delete` | Delete file / directory |
| `filesystem.write` | Coarse umbrella for any write-side check |

At execution time the capability checks the permission required for the named
operation. The Execution Engine owns ask/allow/deny policy and audit.

# Result Model

Callers always observe a `CapabilityResult` from `CapabilityInvoker` (or an
execution result from the engine).

Success payloads include `operation`, `target`, `success`, and operation-specific
data (`content`, `entries`, `metadata`, `destination`, and similar).

Structured failure codes include:

| Code | Meaning |
| --- | --- |
| `permission_denied` | Required filesystem permission not granted |
| `file_not_found` | Target path does not exist |
| `invalid_path` | Blank/null/escaped/outside-root path |
| `unsupported_operation` | Unknown operation |
| `not_a_file` | File operation used on a non-file |
| `not_a_directory` | Directory operation used on a non-directory |
| `not_text_file` | `read_file` could not decode text |
| `file_too_large` | File exceeds configured read limit |
| `already_exists` / `overwrite_*` | Write conflict under overwrite policy |
| `trash_unavailable` | Trash/recycle delete could not be performed |
| `unsafe_target` | Refused root or other unsafe target |

# Key Decisions

* Filesystem is a Capability, not Automation and not an agent tool loop.
* Safety is root-scoped path normalization, not caller trust.
* Permission enforcement uses `CapabilityContext.granted_permissions`.
* Writes never overwrite silently; see [`FILESYSTEM_WRITE.md`](FILESYSTEM_WRITE.md).
* HTTP/UI/desktop concerns stay outside this package module.

# Related Documents

* [`FILESYSTEM_WRITE.md`](FILESYSTEM_WRITE.md)
* [`CAPABILITY_FRAMEWORK.md`](CAPABILITY_FRAMEWORK.md)
* [`CAPABILITY_EXECUTION.md`](CAPABILITY_EXECUTION.md)
* [`../ARCHITECTURE.md`](../ARCHITECTURE.md)
* [`domains.md`](domains.md)
* [`../STATUS.md`](../STATUS.md)
* [`../ROADMAP.md`](../ROADMAP.md)
