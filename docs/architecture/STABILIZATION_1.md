# Platform Stabilization I

Milestone 30 summary. This pass improved maintainability, consistency, and contributor
navigation without changing user-facing behavior or introducing new capabilities.

---

## Refactors performed

### Dependency injection

- **Workspace resolution** — Extracted `WORKSPACE_HEADER`, `parse_workspace_id()`, and
  `get_default_active_workspace_id()` into `memovi_shared`. Five domain packages
  (documents, memory, search, intelligence, automation) now import the shared
  package-default dependency instead of duplicating identical FastAPI handlers.
- **Composition root unchanged** — `apps/api/src/api/workspace_context.py` still
  overrides workspace resolution with membership-aware validation for production traffic.
- **Retrieval engine factory** — Moved `build_retrieval_engine()` to
  `memovi_search/infrastructure/factories/retrieval_engine_factory.py`. Both the search
  package dependencies and `apps/api/search_integration.py` now use the single factory.

### Dead code removed

- Removed unused memory API schemas: `KnowledgeItemResponse`, `KnowledgeItemListResponse`.
  `ChunkResponse` remains in use by knowledge detail responses.

### Documentation aligned with implementation

- Updated `docs/ENGINEERING_SNAPSHOT.md` — package inventory, memory HTTP routes, shared
  library status, removed references to non-existent `docs/adr/`.
- Updated root `README.md` and `docs/README.md` — removed stale ADR directory references;
  clarified that root `tests/` contains placeholders only.
- Updated package READMEs for `auth`, `documents`, and `shared` to reflect current scope.
- Updated `packages/auth/pyproject.toml` description (removed pre-Milestone-2 wording).
- Updated `packages/auth/src/auth/domain/README.md` — domain layer is fully populated.

### Configuration

- Documented `validate_configuration()` in `apps/api/bootstrap.py` as a reserved startup
  hook for future required-environment validation.

---

## Simplifications made

| Area | Before | After |
| --- | --- | --- |
| Workspace header parsing | Duplicated in 6 files | Single `parse_workspace_id()` in `memovi_shared` |
| Package-default workspace DI | ~15 lines × 5 packages | One-line alias to shared FastAPI dependency |
| Retrieval engine wiring | Duplicated in search deps + composition root | Single factory in search infrastructure |
| Memory API schemas | Unused legacy response types | Removed |

---

## Technical debt removed

- Eliminated copy-pasted workspace ID parsing and HTTP 422 handling across domain packages.
- Eliminated duplicate `build_retrieval_engine` implementation between search and API layers.
- Removed aspirational/stale README content that described unimplemented or outdated scope.
- Removed documentation references to directories that do not exist (`docs/adr/`, populated root `tests/`).

---

## Intentionally unchanged (no user-facing behavior change)

The following inconsistencies were **documented** but not modified in this pass because
fixing them would change API contracts or require large breaking refactors:

### API response envelopes

List endpoints use different field names today (`items`, `conversations`, `workspaces`,
`results`). Standardizing these requires a coordinated client migration.

### Pagination

Only `GET /search` supports `limit`/`offset`. Other list endpoints return full result
sets. Adding pagination changes response semantics.

### Error response format

Domains map errors differently: plain `HTTPException(detail=...)`, intelligence domain
error mapping, and automation capability errors embedded in 200 responses. Unifying these
requires client updates.

### Import root naming

`auth` and `documents` omit the `memovi_` prefix; other packages use `memovi_*`. Renaming
would be a large, cross-repo refactor with no runtime benefit.

### Deprecated search route

`GET /search/semantic` and `SemanticSearch` query remain for backwards compatibility.

### Scaffold packages

`memovi_connectors` and `memovi_contracts` retain empty or early package
structure for future milestones. `memovi_config` is populated (Milestone 36).

### Dual model provider stacks

`memovi_models` (Model Provider Framework) and intelligence-local providers both exist.
Intelligence still uses its own gateway; migration to `memovi_models` is tracked separately.

---

## Future recommendations

1. **Centralize configuration** — Done in Milestone 36 (`memovi_config`).
2. **Standardize list response envelopes** — Adopt `{ items, count }` (or similar) across
   all list endpoints in a versioned API pass.
3. **Add pagination** — Extend memory, documents, conversations, and capability list
   endpoints with consistent `limit`/`offset` parameters.
4. **Unify error responses** — Introduce a shared error envelope and domain-to-HTTP mapping
   helper without breaking existing clients (e.g. via API versioning).
5. **Migrate Intelligence to `memovi_models`** — Retire duplicate provider abstractions.
6. **Import root normalization** — Consider renaming `auth`/`documents` to `memovi_auth`/
   `memovi_documents` in a dedicated refactor milestone.
7. **Remove deprecated `/search/semantic`** — After confirming no clients depend on it.
8. **Populate root integration tests** — Replace `tests/` placeholders with cross-package
   architecture tests.
9. **Durable workflow history** — Replace in-memory workflow history store with persistence.
10. **Architecture Decision Records** — Add `docs/adr/` when the team wants formal ADR tracking;
    remove references until then (done in this pass).

---

## Verification

All existing tests should pass unchanged. Run:

```bash
task test
```

Or package-scoped:

```bash
uv run pytest packages/shared/tests packages/search/tests apps/api/tests -q
```
