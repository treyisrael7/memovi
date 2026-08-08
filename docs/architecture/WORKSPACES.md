# Workspaces

# Purpose

This document describes Memovi workspace ownership, membership, roles, and how
those rules are enforced. It complements
[`AUTHORIZATION.md`](AUTHORIZATION.md), which owns the broader trust model.

# Scope

Workspace lifecycle, membership management, role model (`owner` / `member`),
permission enforcement for owner-only operations, ownership transfer, and
membership audit events.

# Ownership model

A workspace is an ownership boundary for documents, knowledge, conversations,
capabilities, and related platform data. Every authenticated user who can access
a workspace has an explicit membership row in `workspace_memberships`.

Roles are stored on membership and validated by
`VALID_ROLES = {"owner", "member"}`. No additional roles are introduced for V1.

| Role | Meaning |
| --- | --- |
| `owner` | Full membership administration and owner-only workspace settings |
| `member` | Access workspace resources; cannot manage members or owner settings |

Creating a workspace enrolls the creator as `owner`. Registering a user enrolls
them as `member` of the seeded Default Workspace.

# Membership lifecycle

```text
Invite registered user (owner)
        │
        ▼
Membership created (role=member) + audit: member_invited
        │
        ├── Owner removes member → audit: member_removed
        ├── Member leaves → audit: member_left
        └── Owner transfers ownership → demote actor / promote target
              + audit: ownership_transferred
```

Invite targets must already be registered users (looked up by email). There is
no separate invitation-token or email-delivery subsystem in this milestone.

## Rules

* Only an **owner** may invite, remove, or transfer ownership.
* The last owner cannot be removed or leave until ownership is transferred.
* Transfer demotes the previous owner to `member` and promotes the target.
* Any member may leave once they are not the sole owner.
* Listing members requires workspace membership (any role).

# API surface

Existing `/workspaces` routes are extended (no parallel membership API):

| Method | Path | Who |
| --- | --- | --- |
| `GET` | `/workspaces` | Authenticated; includes caller's `role` |
| `GET` | `/workspaces/{id}` | Member; includes caller's `role` |
| `POST` | `/workspaces` | Authenticated; creator becomes owner |
| `GET` | `/workspaces/{id}/members` | Member |
| `POST` | `/workspaces/{id}/members` | Owner — invite by email |
| `DELETE` | `/workspaces/{id}/members/{user_id}` | Owner |
| `POST` | `/workspaces/{id}/transfer-ownership` | Owner |
| `POST` | `/workspaces/{id}/leave` | Member (not sole owner) |

# Permission enforcement

Membership boolean checks continue to gate workspace-scoped APIs via
`get_active_workspace_id` and `AuthorizationService.require_workspace_member`.

Owner-only operations use the same Authorization Service:

* `require_workspace_owner` — used for capability permission-mode changes
* Workspace membership commands enforce owner via shared membership guards
  over the same `workspace_memberships.role` column (no second RBAC system)

Examples of owner-only behavior:

* Invite / remove members
* Transfer ownership
* Configure capability permission modes (`PUT /capabilities/{id}/permission-mode`)

Member-or-better continues to apply for documents, memory, search, chat, and
workflow execution inside a workspace.

# Ownership transfer

`POST /workspaces/{id}/transfer-ownership` with `{ "new_owner_user_id": "..." }`:

1. Actor must be an owner
2. Target must already be a member
3. Actor role → `member`
4. Target role → `owner`
5. Audit event `ownership_transferred` is recorded

# Membership audit

Durable events live in `workspace_membership_events` (workspace-owned, not the
capability execution audit store):

| Event type | When |
| --- | --- |
| `member_invited` | Owner invites a registered user |
| `member_removed` | Owner removes a member |
| `ownership_transferred` | Ownership changes |
| `member_left` | Member leaves |

Fields: `actor_user_id`, `target_user_id`, `event_type`, `workspace_id`,
`detail`, `occurred_at`.

# Desktop

Settings → Workspaces shows:

* Workspace list with the caller's role
* Active workspace member list and role badges
* Invite dialog (owners)
* Remove and ownership-transfer confirmations (owners)
* Leave workspace confirmation

Capability policy controls are editable for owners and read-only for members.

# Related documents

* [`AUTHORIZATION.md`](AUTHORIZATION.md)
* [`DESKTOP_CLIENT.md`](DESKTOP_CLIENT.md)
* [`../STATUS.md`](../STATUS.md)
