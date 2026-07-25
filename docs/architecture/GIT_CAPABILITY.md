# Git Capability

# Purpose

This document defines Memovi's Git Capability: structured repository operations
implemented on the Capability Framework and invoked only through the Capability
Execution Engine.

# Scope

It covers architecture, the operation lifecycle, the permission model, structured
result philosophy, safety, errors, desktop presentation, and auditing.

It does not define terminal shell access, browser automation, or multi-step
automation planning.

# Relationship to ARCHITECTURE.md

[`../ARCHITECTURE.md`](../ARCHITECTURE.md),
[`CAPABILITY_FRAMEWORK.md`](CAPABILITY_FRAMEWORK.md), and
[`CAPABILITY_EXECUTION.md`](CAPABILITY_EXECUTION.md) establish that environment
actions belong to Automation capabilities. This document describes the production
Git Capability in `memovi_automation.git`.

# Architecture

```text
Conversation
    ↓
Intelligence
    ↓
Capability Execution Engine
    ↓
Git Capability
    ↓
Private Git implementation (CLI runner)
    ↓
Structured Result
```

Key rules:

* Intelligence never constructs `git` shell commands.
* Intelligence never calls the Terminal Capability to perform Git work.
* The Git Capability may use a private `git` CLI runner or a library; that choice
  is an implementation detail and must not leak into results or the Intelligence
  surface.
* Production composition registers Git on the Capability Registry and seeds an
  Ask Every Time permission mode.

Capability id: `git`

Package path: `packages/automation/src/memovi_automation/git/`

# Operation Lifecycle

1. **Submit** — client or Intelligence submits
   `CapabilityExecutionRequest(capability_id="git", arguments={operation, repository, …})`.
2. **Authorize** — engine resolves Allow / Ask Every Time / Deny.
3. **Approve** (when required) — desktop shows operation preview for write/network ops.
4. **Execute** — engine grants declared Git permissions into
   `CapabilityContext`, then invokes the capability.
5. **Validate** — capability checks the per-operation permission, resolves the
   repository under allowed roots, and rejects invalid inputs.
6. **Run** — private implementation performs the Git action.
7. **Normalize** — structured result is returned (status, branches, history, diff,
   commit metadata, …). Raw CLI output is not exposed.
8. **Audit** — engine records workspace, repository, operation, timestamp,
   duration, and result summary.

# Supported Operations

| Operation | Permission | Result shape |
| --- | --- | --- |
| `detect_repository` | `git.read` | Repository detection + basic metadata |
| `repository_info` | `git.read` | `RepositoryMetadata` |
| `status` | `git.read` | `RepositoryStatus` (staged/modified/untracked/ignored) |
| `list_branches` | `git.read` | `BranchList` |
| `checkout_branch` | `git.write` | Current branch state |
| `create_branch` | `git.write` | Created branch (+ optional checkout) |
| `stage_files` | `git.write` | Staged paths |
| `unstage_files` | `git.write` | Unstaged paths |
| `commit` | `git.write` | `CommitResult` |
| `commit_history` | `git.read` | `CommitHistory` |
| `diff` | `git.read` | `DiffResult` (file or repository) |
| `fetch` | `git.network` | Compact remote summary |
| `pull` | `git.network` | Compact remote summary |
| `push` | `git.network` | Compact remote summary |

# Structured API Philosophy

Callers receive normalized dictionaries, not porcelain text:

* `RepositoryStatus` — branch, clean flag, staged/modified/untracked/ignored lists
* `BranchList` — current + local/remote branch entries
* `CommitHistory` — commits with sha/short_sha/author/date/subject
* `DiffResult` — capped patch text with truncation flag
* `CommitResult` — sha/short_sha/message/summary
* `RepositoryMetadata` — root, git_dir, branch, detached, head

Do not expose:

* Raw process objects
* Full argv transcripts as the primary payload
* Unparsed `git status` / `git log` dumps
* Credentials or authentication challenge text beyond a normalized error code

# Permission Model

| Permission | Role |
| --- | --- |
| `git.read` | Inspect repository state |
| `git.write` | Local modify (stage/unstage/commit/branch/checkout) |
| `git.network` | Remote operations (fetch/pull/push) |

Engine-level modes still apply to the whole capability:

* Allow
* Ask Every Time (default)
* Deny

Potentially destructive or side-effecting operations (write + network) should
remain behind Ask Every Time in production.

# Safety

* Repository paths must resolve under `GitCapabilityConfig.allowed_roots`
  (`MEMOVI_GIT_ROOTS`, falling back to filesystem roots).
* Timeouts and cancellation terminate the underlying git process.
* Diff output is capped by `max_diff_bytes`.
* Empty commit messages and invalid refs/paths are rejected before execution.

# Errors

Normalized codes include:

| Code | Meaning |
| --- | --- |
| `permission_denied` | Missing read/write/network permission or engine deny |
| `repository_not_found` | Path does not exist |
| `invalid_repository` | Outside roots / not a directory |
| `not_a_git_repository` | Path is not a git worktree |
| `empty_message` | Commit message missing |
| `invalid_ref` / `invalid_paths` | Bad branch/ref/path inputs |
| `merge_conflict` | Conflict reported by git |
| `authentication_failure` | Auth failure |
| `detached_head` | Detached HEAD conflict for the requested action |
| `push_rejected` | Remote rejected a push |
| `timeout` / `git_failed` / `git_not_available` | Execution failures |

Raw stack traces are never returned to clients.

# Desktop

Desktop owns presentation only:

* Repository status rendering
* Branch list / current branch
* Commit history list
* Diff preview
* Approval dialogs for write/network operations
* Progress / cancel for long-running remote ops

No Git business logic belongs in the desktop client.

# Auditing

Every status transition appends an audit entry including:

* Workspace
* Repository (from arguments / result summary)
* Operation
* Timestamp
* Duration
* Result summary (branch/clean/short_sha when available)

Sensitive values follow the shared `redact_arguments` rules.

# Configuration

| Setting / env | Role |
| --- | --- |
| `MEMOVI_GIT_ROOTS` | Allowed repository roots |
| Fallback | Filesystem capability roots |
| `default_timeout_seconds` / `max_timeout_seconds` | Execution bounds |
| `max_diff_bytes` | Diff capture cap |
| `default_history_limit` / `max_history_limit` | History bounds |

# Related Documents

* [`CAPABILITY_FRAMEWORK.md`](CAPABILITY_FRAMEWORK.md)
* [`CAPABILITY_EXECUTION.md`](CAPABILITY_EXECUTION.md)
* [`TERMINAL_CAPABILITY.md`](TERMINAL_CAPABILITY.md)
* [`FILESYSTEM_CAPABILITY.md`](FILESYSTEM_CAPABILITY.md)
* [`../ARCHITECTURE.md`](../ARCHITECTURE.md)
* [`../STATUS.md`](../STATUS.md)
* [`../ROADMAP.md`](../ROADMAP.md)
