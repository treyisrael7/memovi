# Terminal Capability

# Purpose

This document defines Memovi's Terminal Capability: structured operating-system
command execution implemented on the Capability Framework and invoked only
through the Capability Execution Engine.

# Scope

It covers responsibilities, the execution lifecycle, the safety model, timeout
and cancellation behavior, structured results, auditing, and desktop
presentation. It does not define browser, git, or multi-step automation.

# Relationship to ARCHITECTURE.md

[`../ARCHITECTURE.md`](../ARCHITECTURE.md),
[`CAPABILITY_FRAMEWORK.md`](CAPABILITY_FRAMEWORK.md), and
[`CAPABILITY_EXECUTION.md`](CAPABILITY_EXECUTION.md) establish that environment
actions belong to Automation capabilities and must pass through the execution
engine. This document describes the production Terminal Capability in
`memovi_automation.terminal`.

# Responsibilities

The Terminal Capability owns safe, explicit shell-command execution when invoked
through the Capability Framework / Execution Engine.

Supported behavior:

* Execute a command
* Execute in a configured working directory
* Capture stdout, stderr, exit code, and duration
* Accept environment variables
* Enforce execution timeout
* Terminate the process on cancel or timeout

It does **not** own:

* Permission modes (Allow / Ask Every Time / Deny)
* Confirmation prompts
* Audit persistence policy beyond producing redacted argument/result summaries
* LLM tool schemas or direct model access to a shell
* Multi-step automation planning

Capability id: `terminal`

Permission: `terminal.execute`

Package path: `packages/automation/src/memovi_automation/terminal/`

# Integration with the Capability Execution Engine

Production callers must submit through the Capability Execution Engine:

```python
from pathlib import Path

from memovi_automation import (
    CapabilityExecutionEngine,
    CapabilityExecutionRequest,
    CapabilityInvoker,
    CapabilityRegistry,
    InMemoryExecutionAuditStore,
    InMemoryPermissionPolicyStore,
    PermissionMode,
    TerminalCapabilityConfig,
    register_terminal_capability,
)
from memovi_shared import WorkspaceId

registry = CapabilityRegistry()
register_terminal_capability(
    registry,
    TerminalCapabilityConfig.from_roots([Path("/allowed/root")]),
)
engine = CapabilityExecutionEngine(
    registry=registry,
    invoker=CapabilityInvoker(registry=registry),
    permission_policies=InMemoryPermissionPolicyStore(),
    audit_store=InMemoryExecutionAuditStore(),
    default_permission_mode=PermissionMode.ASK_EVERY_TIME,
)

result = engine.submit(
    CapabilityExecutionRequest.create(
        capability_id="terminal",
        workspace_id=WorkspaceId.default(),
        arguments={"command": "git status"},
    )
)
```

The terminal is never exposed directly to the LLM. Intelligence may request an
execution through the engine adapter; it cannot import or invoke
`TerminalCapability` as a model-side tool loop.

# Execution Lifecycle

1. **Submit** — client or Intelligence submits a structured
   `CapabilityExecutionRequest` with `capability_id="terminal"`.
2. **Authorize** — engine resolves permission mode
   (`always_allow` / `ask_every_time` / `deny`).
3. **Approve** (when required) — desktop shows command preview; user Approves
   or Denies.
4. **Execute** — engine marks `executing`, grants `terminal.execute`, and
   invokes the capability through `CapabilityInvoker`.
5. **Run process** — capability validates arguments, resolves working directory,
   starts a shell process, and captures output.
6. **Progress** (best-effort) — partial stdout/stderr may be published to the
   in-flight execution for desktop polling.
7. **Complete** — engine stores `completed`, `failed`, or `cancelled` and
   appends audit entries.

No terminal execution path bypasses the execution engine in production
composition.

# Request Arguments

| Argument | Required | Description |
| --- | --- | --- |
| `command` | yes | Non-empty shell command string |
| `operation` | no | Must be `execute` when provided (default) |
| `working_directory` | no | Path under an allowed root; defaults to first root |
| `env` | no | String map merged into the process environment |
| `timeout_seconds` | no | Positive timeout, capped by config max |

# Structured Result

Success payloads never include raw process objects. They include:

| Field | Meaning |
| --- | --- |
| `operation` | Always `execute` |
| `command` | Executed command |
| `working_directory` | Resolved cwd |
| `exit_code` | Process exit code |
| `stdout` / `stderr` | Captured text (possibly truncated) |
| `duration_seconds` | Wall time for the process |
| `success` | `exit_code == 0` |
| `stdout_truncated` / `stderr_truncated` | Output cap flags |
| `metadata` | Compact exit/duration/timeout summary |

A non-zero exit code is still a completed capability invocation: the engine
status is `completed`, while payload `success` is `false`.

# Safety Model

## Permission modes

Owned by the Capability Execution Engine:

| Mode | Behavior |
| --- | --- |
| Allow (`always_allow`) | Execute immediately |
| Ask Every Time (`ask_every_time`) | `pending_approval` until approve/cancel |
| Deny (`deny`) | Fail with `permission_denied` |

Default seeded mode for terminal is Ask Every Time.

## Working directory roots

Working directories are restricted to
`TerminalCapabilityConfig.allowed_roots`. Paths are normalized and must:

* resolve under an allowed root
* exist
* be directories

Empty commands and invalid working directories are rejected before process start.

## Timeouts

* Capability default: `default_timeout_seconds` (30s)
* Hard cap: `max_timeout_seconds` (300s)
* Per-request `timeout_seconds` is clamped to the hard cap
* On timeout the process tree is terminated and the invocation fails with
  `timeout`

## Output limits

`max_stdout_bytes` and `max_stderr_bytes` (default 1 MiB each) bound captured
streams. Excess output is truncated and flagged; raw unbounded pipes are not
returned.

## Process termination

Cancel and timeout both terminate the child process tree (Windows process-group
/ `taskkill`, POSIX session kill). Cooperative cancellation uses the shared
`CancellationToken`; the runner also performs hard termination so long-running
commands cannot ignore cancel.

# Cancellation

* Pending executions can be cancelled before approval.
* In-flight executions can be cancelled from the engine API / desktop Cancel
  action.
* Cancelled runs return structured engine status `cancelled` with error code
  `cancelled`.
* Partial captured output may remain on the execution record when progress was
  published before termination.

# Auditing

Every status transition appends an `ExecutionAuditEntry` through the engine.

Recorded fields include:

* Timestamp
* Workspace
* Capability id (`terminal`)
* Command (from arguments)
* Working directory (when provided / from result summary)
* Duration
* Exit code (from result summary when available)
* Status / result summary

Redaction:

* Sensitive environment variable keys (`token`, `password`, `secret`, …) are
  replaced with `[REDACTED]`
* `stdout` / `stderr` are never stored in audit arguments
* Full command output is not copied into `result_summary`; only compact fields
  such as `exit_code` and duration are retained

# Desktop Presentation

Desktop owns presentation only:

* Command preview from `metadata.operation_summary`
* Approval dialog (Approve / Deny) for Ask Every Time
* Live `Running…` status while `executing`
* Streaming stdout/stderr when progress is available via polling
* Exit status and captured output on completion / failure
* Cancel control for in-flight terminal runs

# Configuration

| Setting / env | Role |
| --- | --- |
| `MEMOVI_TERMINAL_ROOTS` | Allowed working-directory roots (`os.pathsep`-separated) |
| Fallback | Same roots as filesystem capability when unset |
| `default_timeout_seconds` | Default command timeout |
| `max_timeout_seconds` | Hard timeout ceiling |
| `max_stdout_bytes` / `max_stderr_bytes` | Capture caps |

# Error Codes

| Code | Meaning |
| --- | --- |
| `permission_denied` | Missing `terminal.execute` or engine deny mode |
| `empty_command` | Blank / missing command |
| `invalid_working_directory` | Missing, non-directory, or outside roots |
| `invalid_environment` | Malformed `env` map |
| `invalid_timeout` | Non-positive timeout |
| `unsupported_operation` | Unknown operation name |
| `timeout` | Execution exceeded timeout; process terminated |
| `process_failed` | Process could not be started |
| `cancelled` | Execution cancelled through the engine |

# Key Decisions

* Terminal is a Capability, not an LLM tool and not an agent shell.
* All production execution goes through the Capability Execution Engine.
* Safety is root-scoped cwd validation, timeouts, output caps, and process kill.
* Structured results keep OS process handles internal to the runner.
* Streaming is best-effort progress on the in-flight execution record; final
  capture remains the source of truth.

# Related Documents

* [`CAPABILITY_FRAMEWORK.md`](CAPABILITY_FRAMEWORK.md)
* [`CAPABILITY_EXECUTION.md`](CAPABILITY_EXECUTION.md)
* [`FILESYSTEM_CAPABILITY.md`](FILESYSTEM_CAPABILITY.md)
* [`../ARCHITECTURE.md`](../ARCHITECTURE.md)
* [`../STATUS.md`](../STATUS.md)
* [`../ROADMAP.md`](../ROADMAP.md)
