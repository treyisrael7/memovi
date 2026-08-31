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
| Native packaged auth smoke | `task desktop:smoke:native` or manual checklist | Real packaged WebView cookie jar (register → `/auth/me` → logout → `/auth/me` 401). Local display required; **not CI**. Windows WebView2 is proven; macOS WKWebView and Linux WebKitGTK have a manual path until actually run | operator / host |
| Manual native-app release verification | Release host | Launch the real Tauri window, native dialogs, workflows | operator-driven |

Backend and optional web tests stay in their own workflows.

**Mock smoke** is the fast PR gate. It proves the shell can complete the
critical journey when the API responds correctly. It does **not** prove the
desktop talks to the real backend.

**Live API smoke** closes that gap: real session cookies, real upload to MinIO,
real document processing, real search indexing, real conversation SSE, real
citations, and desktop source navigation. It still runs in **jsdom** via Vitest
+ Testing Library. It does **not** launch the native Tauri window.

**Packaging** proves V1 installers still compile. It does not interact with the
UI and is not native launch or auth testing. Pull-request and main CI artifacts
are **unsigned**. Tag-triggered Releases Authenticode-sign Windows and
Developer ID–sign/notarize macOS, and **fail closed** if those secrets are
missing. Linux `.deb` stays unsigned. The auto-updater is future work.

Two packaging paths exist and must not be confused:

| Path | Workflow | When | What it publishes |
| --- | --- | --- | --- |
| CI compile gate | [`.github/workflows/desktop.yml`](../../.github/workflows/desktop.yml) | every push / pull request | Temporary **unsigned** artifacts (`memovi-desktop-*-bundle`, 14-day retention). **Not** a GitHub Release. Never uses signing secrets. |
| GitHub Release | [`.github/workflows/release.yml`](../../.github/workflows/release.yml) | tags matching `v*.*.*` that equal `v` + `tauri.conf.json` `version` | Freshly built V1 assets. Windows Authenticode-signed; macOS Developer ID signed and notarized; Linux `.deb` unsigned. Checksums cover these final files. |

V1 package files:

| Platform | V1 package | CI artifact (unsigned) | Release asset |
| --- | --- | --- | --- |
| Linux | `.deb` | `memovi-desktop-linux-bundle` | `Memovi_<version>_linux_<arch>.deb` (unsigned) |
| Windows | NSIS `.exe` and MSI `.msi` | `memovi-desktop-windows-bundle` | `Memovi_<version>_windows_<arch>_setup.exe` and `Memovi_<version>_windows_<arch>.msi` (Authenticode) |
| macOS | `.dmg` | `memovi-desktop-macos-bundle` | `Memovi_<version>_macos_<arch>.dmg` (Developer ID + notarization) |

`<arch>` is taken from the GitHub-hosted runner (`runner.arch`: `X64` → `x64`, `ARM64` → `arm64`). Current labels: `ubuntu-latest` and `windows-latest` are x64; `macos-latest` is Apple silicon (arm64), not universal. A `SHA256SUMS.txt` file of those four packages is attached to the Release (checksums, not signatures).

`0.x` tags are published as GitHub **pre-releases**, matching the pre-alpha / public-development versioning in `pyproject.toml` and the README. The packaged app still requires the external FastAPI API, PostgreSQL, and MinIO.

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
| Linux | yes | no | manual test path (WebKitGTK); pending until actually run | no |
| Windows | yes | no | locally proven with WebView2 | no |
| macOS | yes | no | manual test path (WKWebView); pending until actually run | no |

Expected CI runtime:

* Build & mock smoke job: ~3–8 minutes
* Live API smoke job: ~5–12 minutes depending on image pull and Cargo-less Python sync
* Linux packaging job: ~10–30 minutes depending on Cargo cache warmth
* Windows packaging job: ~10–30 minutes depending on Cargo cache warmth
* macOS packaging job: ~10–30 minutes depending on Cargo cache warmth (GitHub-hosted; not run locally on Windows)

### Workflow: GitHub Release (`release.yml`)

Runs only on a pushed tag matching `v*.*.*` (for example `v0.1.0`). It does
**not** run on pull requests or ordinary branch pushes. It does **not** reuse
CI packaging artifacts. Missing Windows or macOS signing secrets **fail the
job**; the workflow does not fall back to unsigned Release assets.

1. `validate-tag` reads `apps/desktop/src-tauri/tauri.conf.json` and fails if
   the tag is not exactly `v` + that version.
2. `package-linux` rebuilds an **unsigned** `.deb` (no Linux signing).
3. `package-windows` imports `WINDOWS_CERTIFICATE` into the runner store,
   builds with Tauri `bundle.windows.certificateThumbprint`, and verifies
   Authenticode on the NSIS `.exe` and MSI.
4. `package-macos` imports `APPLE_CERTIFICATE` into an ephemeral keychain,
   builds with Tauri `APPLE_SIGNING_IDENTITY` plus App Store Connect API
   notarization (`APPLE_API_KEY`, `APPLE_API_ISSUER`, `APPLE_API_KEY_P8`),
   then verifies `codesign` on the `.app` and `stapler validate` on the `.dmg`.
5. `publish` runs only if all three package jobs succeed. SHA-256 sums are
   computed from those **final** assets. `contents: write` is on this job only.

A workflow that references secrets is not proof that a signed Release exists
until this job has succeeded on GitHub with real certificates.

#### Release secrets (names only)

Store these in the GitHub repository secrets. Do not commit values.

| Secret | Purpose |
| --- | --- |
| `WINDOWS_CERTIFICATE` | Base64 of the Authenticode `.pfx` (`certutil -encode certificate.pfx base64cert.txt` or `openssl base64 -A -in certificate.pfx`). Identity should match publisher **Trey Israel**. |
| `WINDOWS_CERTIFICATE_PASSWORD` | Password used when exporting that `.pfx`. |
| `APPLE_CERTIFICATE` | Base64 of the Developer ID Application `.p12` (`openssl base64 -A -in certificate.p12`). |
| `APPLE_CERTIFICATE_PASSWORD` | Password for that `.p12`. |
| `APPLE_SIGNING_IDENTITY` | Codesign identity string, e.g. `Developer ID Application: Trey Israel (TEAMID)`. |
| `APPLE_API_KEY` | App Store Connect API Key ID. |
| `APPLE_API_ISSUER` | App Store Connect Issuer ID. |
| `APPLE_API_KEY_P8` | Contents of the downloaded `AuthKey_<id>.p8` (multiline secret). |

Do not use `TAURI_SIGNING_PRIVATE_KEY` here; that is for the updater, which is
not implemented.

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

# Packaged WebView auth smoke (packaged binary + running API; not in CI)
# Windows: proven path. macOS/Linux: same command on that host; not proven until run.
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
* [ ] If cutting a version tag: Release workflow green
      (`.github/workflows/release.yml`) with signing secrets configured;
      versioned `.deb` (unsigned) / signed NSIS / signed MSI / notarized `.dmg`
      plus `SHA256SUMS.txt`. Confirm Authenticode and `stapler validate` on the
      GitHub run, not only that the workflow file exists.

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
.github/workflows/release.yml
scripts/desktop_release.py
scripts/release_windows_certificate.ps1
scripts/release_windows_verify.ps1
scripts/release_macos_keychain.sh
scripts/release_macos_verify.sh
docs/testing/DESKTOP_TESTING.md
docs/testing/NATIVE_DESKTOP_SMOKE.md
scripts/native_desktop_auth_smoke.py
scripts/test_native_desktop_auth_smoke.py
```

Backend unit/integration tests remain under `packages/*/tests` and Backend CI.
Optional web client remains under Frontend CI. Do not conflate those with
desktop smoke coverage.
