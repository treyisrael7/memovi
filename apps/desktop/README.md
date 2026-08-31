# Memovi Desktop

Flagship Tauri desktop client for Memovi.

This package owns the application shell only: window lifecycle, navigation,
theme, startup experience, and backend connection status. Business logic stays
in the FastAPI platform.

## Prerequisites

* Node.js 24 with pnpm (via repository Corepack / setup)
* Rust toolchain (`rustup`)
* Host C++ / linker toolchain required by Tauri (Visual Studio Build Tools with
  the VC++ workload on Windows)

## Develop

The desktop UI always talks to a **separately started** API. Start
infrastructure, migrate, then the backend, then the shell:

```bash
task docker-up
task db:migrate
task backend     # terminal 1 — FastAPI on 127.0.0.1:8000
task desktop     # terminal 2 — Tauri dev webview on 127.0.0.1:1420
```

`task backend` starts Compose services if needed but does **not** migrate.

From this package:

```bash
pnpm install
pnpm tauri:dev
```

Optional API base override (keep the same hostname as the Vite/Tauri origin so
session cookies stay same-site; defaults match `task backend` on `127.0.0.1`):

```bash
VITE_MEMOVI_API_BASE=http://127.0.0.1:8000 pnpm tauri:dev
```

If the repo lives under OneDrive and Rust fails with a non-writable `target`
directory, point Cargo at a local path:

```powershell
$env:CARGO_TARGET_DIR = "$env:LOCALAPPDATA\memovi-desktop-target"
pnpm tauri:dev
```

## Packaged / `tauri build`

A packaged app embeds the Vite frontend only. It does **not** bundle or start
FastAPI, Python, Postgres, or MinIO. Run the same backend steps as Develop,
then launch the installed/built Memovi binary. It still calls
`http://127.0.0.1:8000`.

Unsigned V1 packages are Linux `.deb`, Windows NSIS `.exe` and MSI, and macOS
`.dmg`. They are compiled in GitHub Actions; they are not signed releases.

Packaged origins therefore receive SameSite=None; Secure; Partitioned. Dev
(`tauri dev`) stays `SameSite=Lax`.

Native WebView cookie behavior is not covered by GitHub Actions. After
packaging, use [`docs/testing/NATIVE_DESKTOP_SMOKE.md`](../../docs/testing/NATIVE_DESKTOP_SMOKE.md)
(`task desktop:smoke:native` or the manual checklist) against a running local
API. Settings → Diagnostics shows **Client origin** so you can confirm the
packaged protocol rather than `tauri dev`.

## Architecture

See [`docs/architecture/DESKTOP_CLIENT.md`](../../docs/architecture/DESKTOP_CLIENT.md).

UI primitives and design tokens are documented in
[`docs/design/DESIGN_SYSTEM.md`](../../docs/design/DESIGN_SYSTEM.md).

## Testing

Unit and critical-path smoke tests use Vitest (Vite-native). Desktop CI and the
release checklist are documented in
[`docs/testing/DESKTOP_TESTING.md`](../../docs/testing/DESKTOP_TESTING.md).

```bash
task desktop:test         # unit + mock smoke
task desktop:smoke        # mock critical path only
task desktop:smoke:live   # real FastAPI (see DESKTOP_TESTING.md)
task desktop:smoke:native # packaged WebView auth (see NATIVE_DESKTOP_SMOKE.md)
task desktop:check        # types, tests, Vite build
```
