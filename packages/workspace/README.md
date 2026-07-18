# Memovi Workspace

Workspace ownership domain boundary.

This package owns the Workspace aggregate, its persistence, and workspace lifecycle APIs. Other domains reference `WorkspaceId` from `memovi-shared` and do not depend on this package's infrastructure.

## Responsibilities

- Create, list, and retrieve workspaces
- Persist workspace metadata
- Seed the Default Workspace used for V1 API fallback

## API

- `POST /workspaces` — create a workspace
- `GET /workspaces` — list workspaces
- `GET /workspaces/{id}` — get a workspace

Active workspace for knowledge APIs is resolved in `apps/api` from optional `X-Memovi-Workspace-Id`, falling back to the seeded Default Workspace.

## Does not own

- Document, memory, search, or conversation content
- Authentication or membership/permissions (future)
