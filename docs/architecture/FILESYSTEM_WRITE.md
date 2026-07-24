# Filesystem Write Capability

# Purpose

This document defines Memovi's trusted filesystem write surface: creating,
modifying, moving, copying, renaming, and deleting files and directories through
the Filesystem Capability and Capability Execution Engine.

# Scope

It covers supported write operations, overwrite behavior, deletion behavior,
the permission model, safety philosophy, structured results, and audit
expectations. It does not cover recursive watches, bulk sync tools, or desktop
local filesystem access outside the platform API.

# Relationship to Other Docs

* [`FILESYSTEM_CAPABILITY.md`](FILESYSTEM_CAPABILITY.md) — read model and shared
  root-scoped safety baseline
* [`CAPABILITY_EXECUTION.md`](CAPABILITY_EXECUTION.md) — permission modes,
  approval, audit pipeline
* [`CAPABILITY_FRAMEWORK.md`](CAPABILITY_FRAMEWORK.md) — registry and invoker
* [`../ARCHITECTURE.md`](../ARCHITECTURE.md) — platform blueprint

# Safety Philosophy

Memovi must perform common filesystem tasks without exposing unrestricted OS
access. Every write is:

* **Explicit** — invoked only through a named capability operation
* **Auditable** — recorded by the Capability Execution Engine
* **Permission-controlled** — fine-grained create / modify / move / delete checks
* **Predictable** — no silent overwrites; trash by default when deleting

Workspace isolation remains root-scoped. Path traversal, null bytes, symlink
escapes, and targets outside configured roots fail with `invalid_path`. Allowed
roots themselves cannot be deleted or renamed (`unsafe_target`).

No write operation bypasses the Capability Execution Engine in production. Direct
`Capability.execute` / invoker use is limited to tests and composition-root
wiring.

# Supported Operations

| Operation | Permission | Notes |
| --- | --- | --- |
| `create_file` | `filesystem.create` | Requires `content`; never overwrites silently |
| `create_directory` | `filesystem.create` | Parents created as needed |
| `replace_file_contents` | `filesystem.modify` | Target file must already exist |
| `append_to_file` | `filesystem.modify` (+ `create` if missing) | Appends text; may create file |
| `write_file` | `filesystem.modify` (+ `create` if missing) | Compatibility alias for create/replace |
| `rename_file` / `rename_directory` | `filesystem.move` | Requires `destination` |
| `copy_file` / `copy_directory` | `filesystem.move` | Requires `destination` |
| `move_file` / `move_directory` | `filesystem.move` | Requires `destination` |
| `delete_file` / `delete_directory` | `filesystem.delete` | Trash by default |

Compatibility aliases: `rename_path`, `move_path`, `delete_path` resolve to the
file or directory variant based on the source type.

All existing read operations continue to work unchanged in intent:
`read_file`, `read_directory`, `list_directory`, `exists`, `get_metadata`.

# Overwrite Behavior

Argument: `overwrite_policy`

| Policy | Behavior when destination exists |
| --- | --- |
| `reject` (default) | Fail with `overwrite_rejected` or `already_exists` |
| `ask_user` | Fail with `overwrite_confirmation_required`; desktop/Intelligence may retry with `replace` |
| `replace` | Replace the existing file or directory, then complete the operation |

Nothing overwrites an existing path unless the caller explicitly chooses
`replace` (or confirms after `ask_user`).

# Deletion Behavior

Argument: `delete_mode`

| Mode | Behavior |
| --- | --- |
| `trash` (default) | Move to Recycle Bin / Trash when the platform supports it |
| `permanent` | Irreversible delete; only when explicitly requested and allowed by config |

Successful trash deletes include undo messaging in result metadata
(`undo_available`, `undo_message`). Permanent deletes set `undo_available` to
false. If trash is unavailable, the operation fails with `trash_unavailable`
rather than silently falling back to permanent deletion.

# Permission Model

| Permission | Covers |
| --- | --- |
| `filesystem.read` | All read operations |
| `filesystem.create` | `create_file`, `create_directory` |
| `filesystem.modify` | `replace_file_contents`, `append_to_file`, `write_file` |
| `filesystem.move` | rename / copy / move operations |
| `filesystem.delete` | delete operations |
| `filesystem.write` | Coarse umbrella that satisfies any write-side check |

The Capability Execution Engine still owns workspace permission modes
(`always_allow`, `ask_every_time`, `deny`) and approval before invoke. Fine-
grained permissions are enforced inside the capability using
`CapabilityContext.granted_permissions`.

# Structured Results

Successful write payloads include:

* `operation`
* `target`
* `success` (`true`)
* `metadata` (encoding, size, overwrite/delete policy, undo info, …)
* `destination` when relevant

Failures are returned as structured `CapabilityError` values with stable codes.
Raw exceptions are never returned to callers.

Duration lives on the invoker / execution result envelope.

# Audit

Every write execution creates audit records through the Capability Execution
Engine. Records capture:

* Workspace
* User action source
* Operation and target (from arguments / result summary)
* Timestamp
* Result (status, success, error code/message)

File `content` and other sensitive argument keys are redacted to `[REDACTED]`.

# Desktop Presentation

Desktop displays confirmation, progress, success, failure, and undo messaging
for capability executions. It contains no filesystem logic and only calls the
Capability Execution Engine over HTTP.

# Configuration

`FilesystemCapabilityConfig` write-related fields:

* `max_write_bytes` — content size limit
* `default_overwrite_policy` — `reject` by default
* `default_delete_mode` — `trash` by default
* `allow_permanent_delete` — host can disable permanent deletes

# Key Decisions

* Writes extend the existing `filesystem` capability; there is no parallel API.
* Silent overwrite is never allowed.
* Trash is preferred; permanent delete is explicit.
* Fine-grained permissions coexist with a coarse `filesystem.write` umbrella.
* Safety remains root-scoped path normalization, not caller trust.

# Related Documents

* [`FILESYSTEM_CAPABILITY.md`](FILESYSTEM_CAPABILITY.md)
* [`CAPABILITY_EXECUTION.md`](CAPABILITY_EXECUTION.md)
* [`CAPABILITY_FRAMEWORK.md`](CAPABILITY_FRAMEWORK.md)
* [`DESKTOP_CLIENT.md`](DESKTOP_CLIENT.md)
* [`../STATUS.md`](../STATUS.md)
* [`../ROADMAP.md`](../ROADMAP.md)
