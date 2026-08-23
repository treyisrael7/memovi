# Authorization & Capability Security

# Purpose

This document describes Memovi's server-owned authentication and authorization
model for platform APIs and capability execution. Clients may request actions;
they never decide authorization.

# Relationship to ARCHITECTURE.md

Identity begins in `packages/auth`. Workspace membership lives in
`packages/workspace`. Capability permission policy evaluation and audit
persistence live in `packages/automation`, composed by `apps/api`.

See also [`CAPABILITY_EXECUTION.md`](CAPABILITY_EXECUTION.md) for the execution
pipeline that consumes authorization decisions.

# Trust Boundaries

| Boundary | Trusted? | Notes |
| --- | --- | --- |
| Session cookie (`memovi_session`) | Yes, after server validation | Opaque token; DB stores SHA-256 hash |
| `X-Memovi-Workspace-Id` header | Not alone | Must identify an existing workspace the user belongs to |
| Client `permission_mode` / auth flags | No | Removed from public request contracts |
| Capability implementations | No for authz | They only check engine-granted permissions |
| Authorization Service | Yes | Sole owner of membership + capability policy decisions |

# Authentication

Every non-public HTTP endpoint executes inside an authenticated user context.

**Public endpoints**

* `GET /health`
* `GET /ready`
* `POST /auth/register`
* `POST /auth/login`
* OpenAPI / docs surfaces

**Authentication middleware** rejects missing or invalid session cookies with
`401` before route handlers run. Auth dependencies also resolve
`AuthenticatedPrincipal` (`user_id`, `session_id`, `email`) and bind
`RequestContext.principal` for observability.

Session cookies are HttpOnly. SameSite is **Lax** for same-site local clients
(Tauri dev on `:1420`, optional web on `:3000`, and requests with no packaged
Tauri `Origin`). Packaged Tauri uses a custom-protocol Origin that is cross-site
to `http://127.0.0.1:8000`, so those Origins receive **SameSite=None; Secure**
so credentialed `fetch` can store and send the cookie. That flag is not applied
globally. The `Secure` attribute is also set for any HTTPS API request. Local
dev HTTP without a packaged Origin omits `Secure` so `task desktop` can persist
sessions against `http://127.0.0.1:8000`.

# Workspace Membership

Workspace selection validates membership. The optional workspace header is an
ownership selector, not an authorization token.

* Omitted header → seeded Default Workspace
* Explicit header → workspace must exist
* Authenticated user must be a member (`workspace_memberships`)

Creating a workspace enrolls the creator as `owner`. Registering a user enrolls
them as `member` of the Default Workspace. Listing workspaces returns only
workspaces the caller belongs to (including the caller's `role`).

Membership administration (invite, remove, transfer, leave) is documented in
[`WORKSPACES.md`](WORKSPACES.md). Roles are enforced through the same membership
table — there is no parallel RBAC system.

Owner-only operations (examples):

* Invite / remove members; transfer ownership
* Change capability permission modes
  (`AuthorizationService.require_workspace_owner`)

Member-or-better continues to gate workspace-scoped knowledge APIs via
`require_workspace_member` / active workspace resolution.

# Authorization Service

`CapabilityAuthorizationService` is the server-owned Authorization Service for
capability execution.

Responsibilities:

1. Resolve current user / session (from `AuthenticatedExecutionContext` inputs)
2. Evaluate workspace membership (`require_workspace_member`)
3. Evaluate workspace ownership when required (`require_workspace_owner`)
4. Resolve capability permission mode from durable server policy storage
5. Return an authorization decision and effective permissions

Capabilities never evaluate authorization themselves. After allow/approve, the
Capability Execution Engine grants declared metadata permissions into
`CapabilityContext.granted_permissions`.

# Capability Policies

Policies are entirely server-owned and workspace-scoped:

| Mode | Behavior |
| --- | --- |
| `always_allow` | Execute immediately after authorization |
| `ask_every_time` | Return `pending_approval`; clients only display the approval request |
| `deny` | Fail with `permission_denied` without invoking |

Resolution order:

1. Durable workspace policy store for the capability
2. Engine default (`ask_every_time`)

Clients may update policy only through authenticated
`PUT /capabilities/{id}/permission-mode`. Request bodies must not include
authorization decision fields.

# Authenticated Execution Context

Capability execution requires `AuthenticatedExecutionContext`:

* User ID
* Workspace ID
* Session ID
* Effective permissions
* Request ID

Plus cancellation / conversation / correlation metadata used by the pipeline.
No capability receives unauthenticated context.

# Execution Lifecycle

```text
Client / Intelligence
        │  (authenticated session + workspace membership)
        ▼
Authorization Service
   ├─ membership check
   ├─ capability policy mode
   └─ AuthenticatedExecutionContext + decision
        │
        ▼
Capability Execution Engine
   ├─ deny → fail + audit
   ├─ ask_every_time → pending_approval + audit
   └─ always_allow / approved → invoke + audit
        │
        ▼
Capability (checks granted_permissions only)
```

Filesystem, Terminal, Git, Browser, and Workflow all rely exclusively on
Authorization Service decisions via the engine. Workflows and plans thread the
same authenticated context into every step submission.

# Audit

Capability audits are durable (`automation_execution_audits`) and survive
process restarts. Each transition records:

* User
* Workspace
* Capability
* Operation (when present)
* Timestamp
* Result / status
* Duration
* Redacted arguments and result summary

List via `GET /capabilities/executions/audit`.

# API Contract Rules

Clients must not submit:

* `permission_mode` on execution requests
* `approval_mode`
* other authorization decision flags

Clients may:

* Authenticate
* Select a workspace they belong to
* Request capability execution
* Approve or cancel pending executions
* Display server-owned policy and approval state
