# Memovi Shared

Shared low-level utilities and primitives that are genuinely cross-cutting across Memovi. Domain-specific behavior should stay in the owning package, not here.

## WorkspaceId

`WorkspaceId` is the platform-wide ownership identifier. Knowledge domains (documents, memory, search, intelligence) reference this value object without depending on the Workspace aggregate or its persistence.

The seeded Default Workspace ID (`DEFAULT_WORKSPACE_ID`) supports V1 backwards-compatible API fallback when no active workspace header is supplied.
