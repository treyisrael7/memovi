# Memovi Workspace

Workspace ownership domain boundary.

This package owns the Workspace aggregate, its persistence, and workspace lifecycle APIs. Other domains reference `WorkspaceId` from `memovi-shared` and do not depend on this package's infrastructure.

## Responsibilities

- Create, list, and retrieve workspaces
- Persist workspace metadata and membership
- Seed the Default Workspace used for V1 API fallback
- Enroll creators as workspace owners; enroll new users in Default Workspace

## API

- `POST /workspaces` — create a workspace (authenticated; creator becomes owner)
- `GET /workspaces` — list workspaces the authenticated user belongs to
- `GET /workspaces/{id}` — get a workspace (membership required)

Active workspace for knowledge APIs is resolved in `apps/api` from optional
`X-Memovi-Workspace-Id`, falling back to the seeded Default Workspace, after
authentication and membership validation. See
[`docs/architecture/AUTHORIZATION.md`](../../docs/architecture/AUTHORIZATION.md).

## Does not own

- Document, memory, search, or conversation content
- Session authentication (owned by `packages/auth`)
- Capability permission modes (owned by `packages/automation`)
