# Native desktop authentication smoke

How to verify Memovi session cookies in a **real packaged Tauri WebView**, not in
TestClient or jsdom.

This is maintainer/host evidence. It is **not** part of `task ci` and is **not**
run in GitHub Actions. Linux, unsigned Windows, and unsigned macOS packaging CI
compile packaged bundles; they do not drive WebKitGTK, WebView2, or WKWebView.

---

## Why this exists

The API sets origin-scoped cookie flags:

| Client | Origin | Cookie |
| --- | --- | --- |
| `task desktop` / `tauri dev` | `http://127.0.0.1:1420` | `HttpOnly; SameSite=Lax` |
| Packaged Windows/Android (Tauri 2.11, `useHttpsScheme` unset) | `http://tauri.localhost` | `HttpOnly; SameSite=None; Secure; Partitioned` |
| Packaged Linux/macOS (Tauri 2.11) | `tauri://localhost` | `HttpOnly; SameSite=None; Secure; Partitioned` |
| Optional web | `http://127.0.0.1:3000` | `HttpOnly; SameSite=Lax` |

Packaged origins therefore receive SameSite=None; Secure; Partitioned. That is
scoped to those Origins only. WebView2 treats `http://tauri.localhost` →
`http://127.0.0.1:8000` as a third-party cookie; unpartitioned SameSite=None is
not stored. `Partitioned` opts into CHIPS. Native proof is
[`NATIVE_DESKTOP_SMOKE.md`](NATIVE_DESKTOP_SMOKE.md).

jsdom live smoke uses a test-only cookie bridge. That is not a native jar.

---

## What this repository actually uses

From this repo's `apps/desktop/src-tauri/tauri.conf.json` and Tauri **2.11.5**
`tauri_protocol_url`:

* `devUrl` is `http://127.0.0.1:1420` (development only).
* Packaged `frontendDist` is the Vite `dist` directory, served on the custom
  protocol above. `useHttpsScheme` is **not** set, so Windows stays
  `http://tauri.localhost` rather than `https://tauri.localhost`.
* `https://tauri.localhost` remains in the API allowlist for engines that enable
  the HTTPS custom scheme.

Do not assume the Origin. Record it from **Settings → Diagnostics → Client origin**
or from the automated probe report.

---

## Option A — manual packaged smoke (always valid)

Requires the supported runtime contract:

1. `task docker-up`
2. `task db:migrate`
3. `task backend`
4. Launch the **packaged** app (`tauri build` / installer), not `task desktop`

Print the same checklist with:

```bash
task desktop:smoke:native -- --manual
```

| Step | What you do | Evidence that counts |
| --- | --- | --- |
| 1. API | Backend already running | `GET http://127.0.0.1:8000/ready` succeeds |
| 2. Packaged app | Open the built/installed Memovi window | Native window; **not** Vite on port 1420 |
| 3. Origin | Settings → Diagnostics | Client origin is a packaged Tauri Origin listed above |
| 4. Register or login | Auth gate | Shell enters the product (home/workspace). HttpOnly cookies are **not** visible in JS |
| 5. `/auth/me` | Stay in the product after auth | The shell restored or kept the session via credentialed `GET /auth/me` in this WebView |
| 6. Reload (optional) | Reload the window | Still signed in ⇒ jar survived reload |
| 7. Logout | Sign out | Auth gate returns |
| 8. Unauthenticated `/auth/me` | Stay signed out | No session restore; protected UI stays behind the auth gate |

Relaunch after quit is optional extra evidence (same jar / OS profile).

If Client origin is `http://127.0.0.1:1420`, you are on `tauri dev`. That only
proves SameSite=Lax. Stop and use a packaged binary.

---

## Option B — local automated probe (`task desktop:smoke:native`)

Smallest automation that still uses the **real WebView cookie jar**:

1. Helper checks `GET /ready`.
2. Helper starts a loopback report listener (stdlib HTTP, not a sidecar API).
3. Helper launches an existing **packaged** binary with:
   * `MEMOVI_NATIVE_AUTH_SMOKE=1`
   * `MEMOVI_NATIVE_AUTH_SMOKE_API`
   * `MEMOVI_NATIVE_AUTH_SMOKE_REPORT`
   * `MEMOVI_NATIVE_AUTH_SMOKE_PROFILE` (unique temporary WebView data directory)
4. The Rust host, **only when that env is set**, applies the temporary profile
   as the WebView data directory and `eval`s a one-shot script after the app URL
   finishes loading. Production launches never set these variables.
5. That script `fetch`es `/auth/register` → `/auth/me` → `/auth/logout` →
   `/auth/me` (and a repeat `/auth/me`) with `credentials: "include"` and
   `cache: "no-store"` from `location.origin`. Requests include
   `X-Memovi-Native-Smoke: 1` so the API may echo Set-Cookie **attributes** and
   hashed Cookie fingerprints (not raw session IDs).
6. It POSTs a JSON report (origin, step statuses, emails, cookie attribute
   summaries). It does **not** echo the session token. `document.cookie` is
   recorded only to confirm HttpOnly (it should be empty).
7. The helper kills the app and asserts:
   * origin is a packaged Tauri Origin (dev origin is an explicit fail)
   * `/auth/me` was 200 after register for the email created in this run
   * `/auth/me` was 401 after logout (and on the repeat GET)

This is **not** Selenium/WebDriver/Playwright. It does **not** run in CI (no
guaranteed display; Linux would need xvfb, which this project refuses to add
for fake coverage).

```bash
task docker-up
task db:migrate
task backend                 # terminal 1
pnpm --filter @memovi/desktop tauri:build   # once, if no binary
task desktop:smoke:native    # terminal 2
```

Point at a binary explicitly:

```bash
uv run python scripts/native_desktop_auth_smoke.py --binary path/to/memovi-desktop.exe
```

`tauri build --debug` still uses the packaged custom protocol (not Vite `:1420`).
Pass `--allow-debug` if you only have a debug artifact:

```bash
uv run python scripts/native_desktop_auth_smoke.py --allow-debug
```

If no binary is found, the command exits **2** and tells you to build. That is
not a cookie-jar failure.

### What the probe does **not** prove

* Reload or quit/relaunch persistence
* React UI lifecycle (it bypasses the auth form; it still uses the same
  `fetch` + cookie jar the UI uses)
* Linux WebKitGTK or macOS WKWebView unless you run it on those hosts
* GitHub Actions / headless Linux

---

## Option C — CI posture (honest)

| Job | Cookie jar |
| --- | --- |
| Backend pytest CORS / `Set-Cookie` | None (TestClient) |
| `desktop-live-smoke` | jsdom + test cookie bridge |
| `desktop-package` | Compiles Linux bundle; does not log in |
| `desktop-package-windows` | Compiles unsigned Windows NSIS/MSI (as produced); does not log in |
| `desktop-package-macos` | Compiles an unsigned macOS `.app` / `.dmg` (as produced); does not log in |
| `task desktop:smoke:native` | Real WebView, **local only** |

Keep CI as-is. Do not add WebDriver or xvfb to claim native coverage.

---

## Security notes (for this smoke, not a design rewrite)

**Loopback `Secure` cookies.** Chromium treats `http://127.0.0.1` as a
potentially trustworthy origin. **Observed on Windows WebView2 (this repo,
2026-08-23):** `SameSite=None; Secure` without `Partitioned` was **not** stored
(register 201, then `GET /auth/me` 401). With `Partitioned` (CHIPS),
`GET /auth/me` returned 200 from the real jar. **Observed 2026-08-25:** after
matching CHIPS deletion attributes (`Max-Age=0` and `Expires=Thu, 01 Jan 1970`)
and a fresh WebView profile, `POST /auth/logout` returned 204 and
`GET /auth/me` returned 401 (cookie count `n=0`). WebKitGTK / WKWebView remain
unproven here.

| Platform/runtime | Cookie store/send | Logout clearing |
| --- | --- | --- |
| Windows WebView2 | Proven (CHIPS `Partitioned`) | Proven (`logout` 204 → `/auth/me` 401) |
| Linux WebKitGTK | unverified unless actually run | unverified unless actually run |
| macOS WKWebView | unverified unless actually run | unverified unless actually run |



**Third-party cookies.** Packaged `http://tauri.localhost` → `127.0.0.1:8000` is
cross-site. Unpartitioned `SameSite=None` is a third-party cookie; WebView2 did
not keep it. `Partitioned` opts into a jar keyed by the Tauri top-level site.

**CSRF.** Partitioned cookies are not sent for other top-level sites. A website
in ordinary Chrome still does not share the WebView jar. Remaining risk is
untrusted content *inside* the Memovi WebView. Origin/Referer checks on mutating
auth routes remain optional hardening, not required for this smoke.

**Allowlist.** Matches Tauri 2.11 in this repo plus the HTTPS custom-scheme
variant. Confirm the live Origin in Diagnostics if a Tauri upgrade changes it.

**CSRF.** `SameSite=None` applies only to packaged Origins. The cookie lives in
the desktop WebView jar, not in the user's ordinary browser. A random website
in Chrome does not share that jar. Remaining risk is untrusted content loaded
*inside* the Memovi WebView (XSS / unexpected navigation). An extra
Origin/Referer check on mutating auth routes would be **future hardening**, not
a requirement to complete this verification.

---

## Related

* [`DESKTOP_TESTING.md`](DESKTOP_TESTING.md) — unit, mock smoke, live jsdom smoke, packaging
* [`../architecture/DESKTOP_CLIENT.md`](../architecture/DESKTOP_CLIENT.md) — client/API contract
* [`../architecture/AUTHORIZATION.md`](../architecture/AUTHORIZATION.md) — cookie policy
