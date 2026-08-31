# Desktop Testing

How Memovi validates the flagship desktop client (`apps/desktop`) before release.

Desktop is a first-class CI citizen. Failures in desktop build, packaging, mock
smoke, or live API smoke fail CI.

This document covers CI, test layers, local commands, expected runtimes, and
release validation. It does not change product behavior.

---

## Test layers

| Layer | Location | Purpose | Typical runtime |
| --- | --- | --- | --- |
| Unit | `apps/desktop/src/**/*.test.ts(x)` | Pure helpers, API client behavior, preference persistence | ~2–5 s |
| Integration (backend) | `packages/**/tests`, API suites | Platform contracts the desktop calls | separate Backend CI |
| Mock critical-path smoke | `apps/desktop/src/smoke/criticalPath.smoke.test.tsx` | Critical UI journey against an in-memory API stub | ~5–15 s |
| Live API smoke | `apps/desktop/src/smoke/liveCriticalPath.smoke.test.tsx` | Same React shell against a real FastAPI process (Postgres + MinIO + worker + search + fake providers) | ~30–90 s after infra is up |
| Packaging | Tauri `tauri build` in CI | Unsigned V1 packages: Linux `.deb`, Windows NSIS `.exe` + MSI `.msi`, macOS `.dmg` | ~10–30 min (cold cache) |
| Native packaged auth smoke | `task desktop:smoke:native` or manual checklist | Real WebView cookie jar (register → `/auth/me` → logout). Local display required; **not CI** | operator / host |
| Manual native-app release verification | Release host | Launch the real Tauri window, native dialogs, workflows | operator-driven |

Backend and optional web tests stay in their own workflows.

**Mock smoke** is the fast PR gate. It proves the shell can complete the
critical journey when the API responds correctly. It does **not** prove the
desktop talks to the real backend.

**Live API smoke** closes that gap: real session cookies, real upload to MinIO,
real document processing, real search indexing, real conversation SSE, real
citations, and desktop source navigation. It still runs in **jsdom** via Vitest
+ Testing Library. It does **not** launch the native Tauri window.

**Packaging** proves the unsigned V1 installers still compile. It does not
interact with the UI and is not native launch or auth testing. Artifacts are
unsigned. Unsigned macOS `.dmg` files are not Gatekeeper-ready; signing and
notarization remain future work. GitHub Releases and the auto-updater are
also future work.

V1 package files (CI artifacts, still unsigned):

| Platform | V1 package | CI artifact |
| --- | --- | --- |
| Linux | `.deb` | `memovi-desktop-linux-bundle` |
| Windows | NSIS `.exe` and MSI `.msi` | `memovi-desktop-windows-bundle` |
| macOS | `.dmg` | `memovi-desktop-macos-bundle` |

**Manual native-app verification** remains required for OS window launch, native
folder dialogs, and host-specific packaging. Packaged WebView session cookies
have a dedicated checklist and an optional local probe in
[`NATIVE_DESKTOP_SMOKE.md`](NATIVE_DESKTOP_SMOKE.md). API tests cover CORS and
`Set-Cookie` flags; jsdom live smoke uses a test cookie bridge. Neither is a
native jar.

---

## Smoke test philosophy

Prefer stable, high-value workflow coverage over brittle UI assertions.

Mock smoke focuses on:

* Application startup (auth gate)
* Authentication
* Workspace loading
* Document list, processing status, and upload
* Search
* Conversation
* Workflow configure & run (API execute call)
* Settings persistence (theme)
* Sign-out / shutdown path

Live API smoke focuses on the knowledge critical path only:

* Register a unique user against the real API
* Upload a unique-phrase document
* Wait for Documents **Ready** (`processing_status=completed`)
* Retry keyword search until the unique phrase is indexed (Ready is not the
  same as Memory/Search/embedding completion)
* Ask a question in Conversations and wait for the fake reasoning SSE answer
* Click a citation and land on the Knowledge/source view

They intentionally avoid:

* Pixel / screenshot comparisons
* Timing-sensitive layout assertions
* Exhaustive page coverage
* Playwright, Cypress, WebDriver, `tauri-driver`, or native window automation

Implementation notes:

* Framework: **Vitest** + Testing Library + jsdom (already Vite-native; no extra E2E framework)
* Mock network: `src/test/mockBackend.ts` stubs critical REST paths in-process
* Live network: real `fetch` / upload XHR to `http://127.0.0.1:8000`
* jsdom origin is `http://127.0.0.1:1420` so SameSite=Lax cookies match the
  desktop client. A test-only cookie bridge (`src/test/liveApiCookies.ts`)
  records `Set-Cookie` and attaches `Cookie` because Node/jsdom do not share a
  browser cookie jar. Production auth is unchanged.
* Live smoke is skipped unless `MEMOVI_LIVE_API=1`
* Mock suite runtime target: **under 30 seconds**. Live smoke timeout: **90 seconds**.

---

## CI pipeline

Workflow: [`.github/workflows/desktop.yml`](../../.github/workflows/desktop.yml)

### Job: `desktop` (build & mock smoke)

Runs on every push / PR:

1. `pnpm install --frozen-lockfile`
2. Typecheck (`tsc --noEmit`)
3. Unit tests (`pnpm test:unit`)
4. Critical-path mock smoke (`pnpm test:smoke`) — does **not** run live smoke
5. Vite production build (`pnpm build`)
6. Upload `apps/desktop/dist` as artifact `memovi-desktop-dist`

Any failure fails CI.

Local Prettier (`task desktop:format-check`) is available; it is not a CI gate
yet because much of the existing shell source predates a shared format pass.

### Job: `desktop-live-smoke` (real API)

Runs on every push / PR, in parallel with the mock smoke job. Sets
`MEMOVI_LIVE_API=1` (CI must not skip this job).

1. Install Node/pnpm and Python/uv dependencies
2. `docker compose up -d` (Postgres + MinIO from the existing Compose file)
3. Wait until Postgres and MinIO are reachable
4. `alembic upgrade head`
5. Start FastAPI with `INTELLIGENCE_PROVIDER=fake`,
   `SEARCH_EMBEDDING_PROVIDER=fake`, and `MEMOVI_OBJECT_STORAGE=minio`
   (not in-memory storage)
6. Wait for `GET /ready`
7. `pnpm test:smoke:live`
8. On failure, dump API and Compose logs
9. Stop the API process and `docker compose down`

This job does **not** install WebKit, xvfb, Redis, or a browser framework, and
it does **not** launch Tauri. Native packaged-origin cookies are documented in
[`NATIVE_DESKTOP_SMOKE.md`](NATIVE_DESKTOP_SMOKE.md), not this job.

### Job: `desktop-package` (Linux packaging)

Runs after `desktop` succeeds:

1. Install Linux WebKit / GTK dependencies
2. Install Rust stable + Cargo cache
3. `pnpm tauri build` from `apps/desktop`
4. List `src-tauri/target/release/bundle` and fail if no `.deb` exists
5. Upload the Linux V1 package (`memovi-desktop-linux-bundle`) from
   `bundle/deb/*.deb`. Missing `.deb` files fail this job
   (`if-no-files-found: error`).

This job does not produce Windows or macOS bundles, RPM, AppImage, or a
raw binary artifact, and it does not sign anything. It does not run live
smoke or native WebView auth.

### Job: `desktop-package-windows` (unsigned Windows packaging)

Runs after `desktop` succeeds, in parallel with Linux packaging, on
`windows-latest`:

1. Install the same Node/pnpm and Rust stable + Cargo cache toolchain
2. `pnpm tauri build` from `apps/desktop` (unsigned; no certificates or
   Authenticode secrets)
3. List files under `src-tauri/target/release/bundle` and fail if either
   NSIS `.exe` or MSI `.msi` is missing
4. Upload generated Windows V1 installers (`memovi-desktop-windows-bundle`)
   from `bundle/nsis/*.exe` and `bundle/msi/*.msi`. Missing installer files
   fail this job (`if-no-files-found: error`).

This job does **not** start FastAPI, Postgres, MinIO, Docker, or Python. It does
**not** set `MEMOVI_NATIVE_AUTH_SMOKE=1`. Native Windows WebView2 auth remains a
local proof (`task desktop:smoke:native`).

### Job: `desktop-package-macos` (unsigned macOS packaging)

Runs after `desktop` succeeds, in parallel with Linux and Windows packaging, on
`macos-latest`:

1. Install the same Node/pnpm and Rust stable + Cargo cache toolchain
2. `pnpm tauri build` from `apps/desktop` (unsigned; no Apple Developer
   credentials, notarization, or signing secrets)
3. List files under `src-tauri/target/release/bundle` and fail if no `.dmg`
   is present (the `.app` is a build intermediate, not a separate V1
   installer artifact)
4. Upload the macOS V1 package (`memovi-desktop-macos-bundle`) from
   `bundle/dmg/*.dmg`. Missing `.dmg` files fail this job
   (`if-no-files-found: error`).

This is an **unsigned macOS `.dmg`**. It is not signed or notarized, so it is
not a Gatekeeper-ready distribution. The job does **not** start FastAPI,
Postgres, MinIO, Docker, or Python. It does **not** set
`MEMOVI_NATIVE_AUTH_SMOKE=1`. Packaging does not prove native WKWebView launch
or auth; those remain unverified until actually tested on macOS.

| Platform | Package CI | Native launch in CI | Native auth | Signing |
| --- | --- | --- | --- | --- |
| Linux | yes | no | unverified | no |
| Windows | yes | no | locally proven with WebView2 | no |
| macOS | yes | no | unverified | no |

Expected CI runtime:

* Build & mock smoke job: ~3–8 minutes
* Live API smoke job: ~5–12 minutes depending on image pull and Cargo-less Python sync
* Linux packaging job: ~10–30 minutes depending on Cargo cache warmth
* Windows packaging job: ~10–30 minutes depending on Cargo cache warmth
* macOS packaging job: ~10–30 minutes depending on Cargo cache warmth (GitHub-hosted; not run locally on Windows)

---

## Local execution

From the repository root:

```bash
# Full desktop check (types, unit+mock smoke, Vite build)
task desktop:check

# Unit + mock smoke
task desktop:test

# Mock smoke only (fast; no API required)
task desktop:smoke

# Live API smoke (requires Postgres, MinIO, migrated DB, and `task backend`)
task desktop:smoke:live

# Packaged WebView auth smoke (built binary + running API; not in CI)
task desktop:smoke:native
task desktop:smoke:native -- --manual

# Vite shell build
task desktop:build

# Typecheck / format
task desktop:typecheck
task desktop:format-check
```

`task desktop:smoke:live` sets `MEMOVI_LIVE_API=1` and runs only the live file.
It does not start infrastructure. Typical local sequence:

```bash
task docker-up
task db:migrate
task backend   # terminal 1; fake providers + MinIO by default
task desktop:smoke:live
```

Without `MEMOVI_LIVE_API=1`, the live test skips cleanly. `task ci` / `task ci:desktop`
stay on the fast mock path and do not start this live job.

From the package:

```bash
pnpm --filter @memovi/desktop test
pnpm --filter @memovi/desktop test:unit
pnpm --filter @memovi/desktop test:smoke
MEMOVI_LIVE_API=1 pnpm --filter @memovi/desktop test:smoke:live
pnpm --filter @memovi/desktop build
```

Native packaging (requires Rust + host Tauri prerequisites):

```bash
pnpm --filter @memovi/desktop tauri:build
```

`task desktop` (`tauri dev`) is **not** packaged-origin proof. For the WebView
cookie jar see [`NATIVE_DESKTOP_SMOKE.md`](NATIVE_DESKTOP_SMOKE.md):

```bash
task backend                 # terminal 1
task desktop:smoke:native    # packaged binary + WebView probe
# or
task desktop:smoke:native -- --manual
```

---

## Release checklist

Use this before tagging or distributing a desktop build. Automated CI covers
build, mock smoke, live API smoke, and packaging. This checklist covers the
native window and host packaging sanity.

### Automated (must be green)

* [ ] Desktop CI `desktop` job green (typecheck, unit, mock smoke, Vite build)
* [ ] Desktop CI `desktop-live-smoke` job green (real FastAPI + MinIO path)
* [ ] Desktop CI `desktop-package` job green (Linux Tauri packaging)
* [ ] Desktop CI `desktop-package-windows` job green (unsigned Windows Tauri packaging)
* [ ] Desktop CI `desktop-package-macos` job green (unsigned macOS Tauri packaging)
* [ ] Artifacts available: `memovi-desktop-dist`, `memovi-desktop-linux-bundle`, `memovi-desktop-windows-bundle`, `memovi-desktop-macos-bundle`

### Manual / host validation

* [ ] Desktop launches (`task desktop` or installed package) with `task backend` already running
* [ ] Authentication works (register / sign in / session restore) — including a **packaged** build, not only `tauri dev`. Follow [`NATIVE_DESKTOP_SMOKE.md`](NATIVE_DESKTOP_SMOKE.md); record Client origin from Diagnostics
* [ ] Workspace loads (Default Workspace visible; navigation works)
* [ ] Document upload works; processing status progresses
* [ ] Search returns results for known content
* [ ] Conversations load and accept a message
* [ ] Native folder dialogs work (Connectors)
* [ ] Workflow execution works (library → configure → run; approvals if prompted)
* [ ] Settings persist across restart (theme / model preference)
* [ ] Sign out returns to auth gate; clean quit
* [ ] Packaging succeeds on the release platform (Windows / macOS / Linux as applicable)

---

## Organization summary

```
apps/desktop/
  src/
    **/*.test.ts(x)                    # unit
    smoke/criticalPath.smoke.test.tsx  # mock critical-path smoke
    smoke/liveCriticalPath.smoke.test.tsx  # live API smoke (MEMOVI_LIVE_API=1)
    test/mockBackend.ts                # in-memory API stub
    test/liveApiCookies.ts             # test-only jsdom cookie bridge
    test/setup.ts                      # Vitest/jsdom setup
.github/workflows/desktop.yml
docs/testing/DESKTOP_TESTING.md
docs/testing/NATIVE_DESKTOP_SMOKE.md
scripts/native_desktop_auth_smoke.py
```

Backend unit/integration tests remain under `packages/*/tests` and Backend CI.
Optional web client remains under Frontend CI. Do not conflate those with
desktop smoke coverage.
