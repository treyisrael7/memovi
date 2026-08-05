# Memovi Shared

Shared low-level utilities and primitives that are genuinely cross-cutting across Memovi.
Domain-specific behavior should stay in the owning package, not here.

## WorkspaceId

`WorkspaceId` is the platform-wide ownership identifier. Knowledge domains (documents,
memory, search, intelligence) reference this value object without depending on the
Workspace aggregate or its persistence.

The seeded Default Workspace ID (`DEFAULT_WORKSPACE_ID`) supports V1 backwards-compatible
API fallback when no active workspace header is supplied.

## Workspace header helpers

- `WORKSPACE_HEADER` — the `X-Memovi-Workspace-Id` request header name
- `parse_workspace_id()` — parse a header value into a `WorkspaceId`
- `memovi_shared.fastapi.get_default_active_workspace_id` — package-default FastAPI
  dependency used by domain routers; the composition root overrides it with
  membership-aware resolution in `apps/api`
