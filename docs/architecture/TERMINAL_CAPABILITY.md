# Terminal Capability

# Purpose

This document defines Memovi's Terminal Capability: structured operating-system
command execution implemented on the Capability Framework and invoked only
through the Capability Execution Engine.

# Scope

It covers responsibilities, the execution lifecycle, the safety model, command
policy / sandboxing, timeout and cancellation behavior, structured results,
auditing, configuration, and desktop presentation. It does not define browser,
git, or multi-step automation.

# Relationship to ARCHITECTURE.md

[`../ARCHITECTURE.md`](../ARCHITECTURE.md),
[`CAPABILITY_FRAMEWORK.md`](CAPABILITY_FRAMEWORK.md),
[`CAPABILITY_EXECUTION.md`](CAPABILITY_EXECUTION.md), and
[`CONFIGURATION.md`](CONFIGURATION.md) establish that environment actions belong
to Automation capabilities, must pass through the execution engine, and load
settings from `memovi_config`. This document describes the production Terminal
Capability in `memovi_automation.terminal`.

# Responsibilities

The Terminal Capability owns safe, explicit command execution when invoked
through the Capability Framework / Execution Engine.

Supported behavior:

* Execute a command under policy + root sandboxing
* Execute in a configured working directory
* Capture stdout, stderr, exit code, and duration
* Accept environment variables
* Enforce execution timeout and output caps
* Terminate the process on cancel or timeout
* Prefer structured argv execution when practical

It does **not** own:

* Workspace membership checks (Authorization Service)
* Capability-level Allow / Ask Every Time / Deny mode storage
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

Before approval / invoke, the engine calls
`TerminalCapability.evaluate_submit_policy` when present. That hook:

* Denies disallowed executables / argument patterns immediately
* Escalates Always Allow → Ask Every Time for confirmation-required commands

# Execution Lifecycle

1. **Submit** — client or Intelligence submits a structured
   `CapabilityExecutionRequest` with `capability_id="terminal"`.
2. **Authorize** — engine resolves capability permission mode
   (`always_allow` / `ask_every_time` / `deny`).
3. **Command policy** — parse command; evaluate allow / deny / confirmation rules.
4. **Approve** (when required) — desktop shows command preview; user Approves
   or Denies. High-risk commands force Ask even when capability mode is Allow.
5. **Execute** — engine marks `executing`, grants `terminal.execute`, and
   invokes the capability through `CapabilityInvoker`.
6. **Run process** — capability re-validates policy, resolves working directory,
   starts the process (argv preferred), and captures output.
7. **Progress** (best-effort) — partial stdout/stderr may be published to the
   in-flight execution for desktop polling.
8. **Complete** — engine stores `completed`, `failed`, or `cancelled` and
   appends audit entries.

No terminal execution path bypasses the execution engine in production
composition.

# Request Arguments

| Argument | Required | Description |
| --- | --- | --- |
| `command` | yes | Non-empty command string (parsed before execution) |
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
| `executable` | Parsed executable basename |
| `working_directory` | Resolved cwd |
| `exit_code` | Process exit code |
| `stdout` / `stderr` | Captured text (possibly truncated) |
| `duration_seconds` | Wall time for the process |
| `success` | `exit_code == 0` |
| `stdout_truncated` / `stderr_truncated` | Output cap flags |
| `shell` | Whether `shell=True` was used |
| `policy` | Policy decision summary |
| `metadata` | Compact exit/duration/timeout/policy summary |

A non-zero exit code is still a completed capability invocation: the engine
status is `completed`, while payload `success` is `false`.

# Execution Policy

Command policy is evaluated **before** process start (submit + execute):

| Rule | Behavior |
| --- | --- |
| Empty / unparseable command | Reject (`empty_command` / `invalid_arguments`) |
| Deny list | Reject (`command_denied`) |
| Allow list (when configured) | Reject executables not listed |
| Denied argument patterns | Reject matching args / raw command |
| Confirmation-required list | Escalate to Ask Every Time when capability mode is Allow |
| Otherwise | Allow |

Safer defaults (overridable via configuration):

* Default deny: `dd`, `mkfs`, `diskpart`, `format`
* Default confirmation-required: destructive / privileged names such as
  `rm`, `sudo`, `chmod`, `shutdown`, …
* Default denied argument patterns: password / token / api-key style flags
* No allow list by default (preserves existing workflow compatibility)

# Safety Model

## Permission modes

Owned by the Capability Execution Engine (capability-level):

| Mode | Behavior |
| --- | --- |
| Allow (`always_allow`) | Execute immediately unless command policy escalates |
| Ask Every Time (`ask_every_time`) | `pending_approval` until approve/cancel |
| Deny (`deny`) | Fail with `permission_denied` |

Default seeded mode for terminal is Ask Every Time.

High-risk commands still require explicit approval under Always Allow via the
confirmation-required policy.

## Working directory roots (sandbox)

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

## Process invocation (shell vs argv)

Where practical, the runner prefers structured argv execution (`shell=False`)
after `shlex` parsing. It falls back to `shell=True` when:

* the command contains shell metacharacters (pipes, redirects, chaining), or
* argv spawn fails with `FileNotFoundError` (common for shell builtins such as
  Windows `echo`), and `allow_shell` is enabled

`shell=True` remains for compatibility. Operators can set
`MEMOVI_TERMINAL_ALLOW_SHELL=false` for stricter hosts that only allow argv
execution of real binaries.

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

# Auditing & Observability

Every status transition appends an `ExecutionAuditEntry` through the engine.

Recorded fields include:

* Timestamp, workspace, capability id (`terminal`)
* Executable basename (when parseable)
* Command (secret-like flags redacted)
* Working directory
* Duration, exit code
* Policy decision and approval status
* Whether shell invocation was used

Redaction:

* Sensitive environment variable keys (`token`, `password`, `secret`, …) are
  replaced with `[REDACTED]`
* Command flags such as `--password=` / `token=` are redacted in audit/UI
  summaries
* `stdout` / `stderr` are never stored in audit arguments

Metrics / logs:

* `memovi.terminal.execution.duration_ms`
* `memovi.terminal.execution.completed` / `nonzero_exit`
* Structured `terminal.execute.start` / `terminal.execute.finish` operations

# Desktop Presentation

Desktop owns presentation only:

* Command preview from `metadata.operation_summary`
* Approval dialog (Approve / Deny) for Ask Every Time / high-risk escalation
* Live `Running…` status while `executing`
* Streaming stdout/stderr when progress is available via polling
* Exit status and captured output on completion / failure
* Cancel control for in-flight terminal runs

# Configuration

All settings load through `memovi_config.CapabilitiesSettings` (no second config
system).

| Setting / env | Role |
| --- | --- |
| `MEMOVI_TERMINAL_ROOTS` | Allowed working-directory roots (`os.pathsep`-separated) |
| Fallback roots | Same as filesystem capability when unset |
| `MEMOVI_TERMINAL_ALLOWED_EXECUTABLES` | Optional allow list (comma-separated) |
| `MEMOVI_TERMINAL_DENIED_EXECUTABLES` | Deny list (comma-separated; unset → defaults) |
| `MEMOVI_TERMINAL_CONFIRM_EXECUTABLES` | Confirmation-required list (unset → defaults) |
| `MEMOVI_TERMINAL_DENIED_ARGUMENT_PATTERNS` | Semicolon-separated regexes (unset → defaults) |
| `MEMOVI_TERMINAL_DEFAULT_TIMEOUT_SECONDS` | Default command timeout |
| `MEMOVI_TERMINAL_MAX_TIMEOUT_SECONDS` | Hard timeout ceiling |
| `MEMOVI_TERMINAL_MAX_STDOUT_BYTES` / `…_STDERR_BYTES` | Capture caps |
| `MEMOVI_TERMINAL_PREFER_ARGV` | Prefer `shell=False` when practical (default true) |
| `MEMOVI_TERMINAL_ALLOW_SHELL` | Allow `shell=True` fallback (default true) |

# Error Codes

| Code | Meaning |
| --- | --- |
| `permission_denied` | Missing `terminal.execute` or engine deny mode |
| `command_denied` | Executable / argument blocked by command policy |
| `empty_command` | Blank / missing command |
| `invalid_arguments` | Unparseable command or invalid policy pattern |
| `invalid_working_directory` | Missing, non-directory, or outside roots |
| `invalid_environment` | Malformed `env` map |
| `invalid_timeout` | Non-positive timeout |
| `unsupported_operation` | Unknown operation name |
| `timeout` | Execution exceeded timeout; process terminated |
| `process_failed` | Process could not be started |
| `cancelled` | Execution cancelled through the engine |

# Limitations

* Command strings remain the primary API for compatibility with existing
  workflows; full elimination of `shell=True` is not guaranteed when shell
  builtins, pipes, or redirects are required.
* Allow lists match executable basenames (not full resolved paths).
* Argument deny patterns are best-effort regexes; they are not a complete
  secret-detection system.
* Working-directory sandboxing does not prevent a permitted executable from
  touching paths outside roots if the OS command itself can (operators should
  combine allow lists + confirmation policy + OS controls).
* Resume-after-approval of multi-step workflows is owned by Workflow Automation,
  not this capability.

# Key Decisions

* Terminal is a Capability, not an LLM tool and not an agent shell.
* All production execution goes through the Capability Execution Engine.
* Safety combines capability permission modes, command policy, root-scoped cwd
  validation, timeouts, output caps, and process kill.
* Safer defaults favor deny/confirm for high-risk names without breaking common
  workflows (no default allow list).
* Structured results keep OS process handles internal to the runner.

# Related Documents

* [`CAPABILITY_FRAMEWORK.md`](CAPABILITY_FRAMEWORK.md)
* [`CAPABILITY_EXECUTION.md`](CAPABILITY_EXECUTION.md)
* [`CONFIGURATION.md`](CONFIGURATION.md)
* [`FILESYSTEM_CAPABILITY.md`](FILESYSTEM_CAPABILITY.md)
* [`../ARCHITECTURE.md`](../ARCHITECTURE.md)
* [`../STATUS.md`](../STATUS.md)
* [`../ROADMAP.md`](../ROADMAP.md)
