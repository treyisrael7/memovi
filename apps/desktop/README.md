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

Start the backend in one terminal:

```bash
task backend
```

Start the desktop shell:

```bash
task desktop
```

Or from this package:

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
task desktop:check        # types, tests, Vite build
```
