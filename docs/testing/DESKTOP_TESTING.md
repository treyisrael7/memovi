# Desktop Testing

How Memovi validates the flagship desktop client (`apps/desktop`) before release.

Desktop is a first-class CI citizen. Failures in desktop build, packaging, or
critical-path smoke tests fail CI.

This document covers CI, test layers, local commands, expected runtimes, and
release validation. It does not change product behavior.

---

## Test layers

| Layer | Location | Purpose | Typical runtime |
| --- | --- | --- | --- |
| Unit | `apps/desktop/src/**/*.test.ts(x)` | Pure helpers, API client behavior, preference persistence | ~2–5 s |
| Integration (backend) | `packages/**/tests`, API suites | Platform contracts the desktop calls | separate Backend CI |
| Desktop smoke | `apps/desktop/src/smoke/*.smoke.test.tsx` | Critical user journey against an in-memory API stub | ~5–15 s |
| Packaging | Tauri `tauri build` in CI | Native bundle still produces installable artifacts | ~10–30 min (cold cache) |

Backend and optional web tests stay in their own workflows. Desktop smoke tests
do **not** replace API integration tests; they prove the shell can complete the
critical journey when the API responds correctly.

---

## Smoke test philosophy

Prefer stable, high-value workflow coverage over brittle UI assertions.

Smoke tests focus on:

* Application startup (auth gate)
* Authentication
* Workspace loading
* Document list, processing status, and upload
* Search
* Conversation
* Workflow configure & run (API execute call)
* Settings persistence (theme)
* Sign-out / shutdown path

They intentionally avoid:

* Pixel / screenshot comparisons
* Timing-sensitive layout assertions
* Exhaustive page coverage

Implementation notes:

* Framework: **Vitest** + Testing Library + jsdom (already Vite-native; no extra E2E framework)
* Network: `src/test/mockBackend.ts` stubs critical REST paths in-process
* Runtime target: **under 30 seconds** for the full desktop Vitest suite locally or in CI

---

## CI pipeline

Workflow: [`.github/workflows/desktop.yml`](../../.github/workflows/desktop.yml)

### Job: `desktop` (build & smoke)

Runs on every push / PR:

1. `pnpm install --frozen-lockfile`
2. Typecheck (`tsc --noEmit`)
3. Unit tests (`pnpm test:unit`)
4. Critical-path smoke (`pnpm test:smoke`)
5. Vite production build (`pnpm build`)
6. Upload `apps/desktop/dist` as artifact `memovi-desktop-dist`

Any failure fails CI.

Local Prettier (`task desktop:format-check`) is available; it is not a CI gate
yet because much of the existing shell source predates a shared format pass.

### Job: `desktop-package` (packaging)

Runs after `desktop` succeeds:

1. Install Linux WebKit / GTK dependencies
2. Install Rust stable + Cargo cache
3. `pnpm tauri build` from `apps/desktop`
4. Upload Linux bundle artifacts (`memovi-desktop-linux-bundle`)

Packaging failures fail CI.

Expected CI runtime:

* Build & smoke job: ~3–8 minutes
* Packaging job: ~10–30 minutes depending on Cargo cache warmth

---

## Local execution

From the repository root:

```bash
# Full desktop check (types, unit+smoke, Vite build)
task desktop:check

# Unit + smoke
task desktop:test

# Smoke only
task desktop:smoke

# Vite shell build
task desktop:build

# Typecheck / format
task desktop:typecheck
task desktop:format-check
```

From the package:

```bash
pnpm --filter @memovi/desktop test
pnpm --filter @memovi/desktop test:unit
pnpm --filter @memovi/desktop test:smoke
pnpm --filter @memovi/desktop build
```

Native packaging (requires Rust + host Tauri prerequisites):

```bash
pnpm --filter @memovi/desktop tauri:build
```

Manual product smoke against a live backend:

```bash
task backend   # terminal 1
task desktop   # terminal 2
```

Then walk the [release checklist](#release-checklist) below.

---

## Release checklist

Use this before tagging or distributing a desktop build. Automated CI covers
build, packaging, and critical-path smoke; this checklist covers live backend
and packaging sanity on the release host.

### Automated (must be green)

* [ ] Desktop CI `desktop` job green (format, typecheck, unit, smoke, Vite build)
* [ ] Desktop CI `desktop-package` job green (Tauri packaging)
* [ ] Artifacts available: `memovi-desktop-dist`, `memovi-desktop-linux-bundle` (or platform equivalent)

### Manual / host validation

* [ ] Desktop launches (`task desktop` or installed package)
* [ ] Authentication works (register / sign in / session restore)
* [ ] Workspace loads (Default Workspace visible; navigation works)
* [ ] Document upload works; processing status progresses
* [ ] Search returns results for known content
* [ ] Conversations load and accept a message
* [ ] Workflow execution works (library → configure → run; approvals if prompted)
* [ ] Settings persist across restart (theme / model preference)
* [ ] Sign out returns to auth gate; clean quit
* [ ] Packaging succeeds on the release platform (Windows / macOS / Linux as applicable)

---

## Organization summary

```
apps/desktop/
  src/
    **/*.test.ts(x)          # unit
    smoke/*.smoke.test.tsx   # critical-path smoke
    test/mockBackend.ts      # in-memory API stub
    test/setup.ts            # Vitest/jsdom setup
.github/workflows/desktop.yml
docs/testing/DESKTOP_TESTING.md
```

Backend unit/integration tests remain under `packages/*/tests` and Backend CI.
Optional web client remains under Frontend CI. Do not conflate those with
desktop smoke coverage.
