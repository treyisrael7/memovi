"""Launch a packaged Memovi desktop binary and observe WebView session cookies.

This is not CI coverage. It requires a built Tauri binary, a display, and a
running API. It does not use WebDriver, Playwright, or xvfb.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import urlopen

PACKAGED_TAURI_ORIGINS = frozenset(
    {
        "tauri://localhost",
        "https://tauri.localhost",
        "http://tauri.localhost",
    }
)

DEV_DESKTOP_ORIGIN = "http://127.0.0.1:1420"


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _binary_candidates(*, include_debug: bool) -> list[Path]:
    roots: list[Path] = []
    cargo_target = os.environ.get("CARGO_TARGET_DIR")
    if cargo_target:
        roots.append(Path(cargo_target))
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        roots.append(Path(local_app_data) / "memovi-desktop-target")
    home = os.environ.get("HOME") or os.environ.get("USERPROFILE")
    if home:
        roots.append(Path(home) / "memovi-desktop-target")
    roots.append(_repo_root() / "apps" / "desktop" / "src-tauri" / "target")

    names = (
        "memovi-desktop.exe",
        "memovi-desktop",
        "Memovi.exe",
        "Memovi",
    )
    candidates: list[Path] = []
    for root in roots:
        profiles = ("debug", "release") if include_debug else ("release",)
        for profile in profiles:
            profile_dir = root / profile
            for name in names:
                candidates.append(profile_dir / name)
            candidates.append(
                profile_dir / "bundle" / "macos" / "Memovi.app" / "Contents" / "MacOS" / "Memovi"
            )
    return candidates


def find_binary(explicit: str | None, *, include_debug: bool = False) -> Path | None:
    if explicit:
        path = Path(explicit)
        return path if path.is_file() else None
    for candidate in _binary_candidates(include_debug=include_debug):
        if candidate.is_file():
            return candidate
    return None


def api_ready(api_base: str, timeout_s: float) -> bool:
    deadline = time.monotonic() + timeout_s
    url = f"{api_base.rstrip('/')}/ready"
    while time.monotonic() < deadline:
        try:
            with urlopen(url, timeout=2) as response:
                if 200 <= response.status < 300:
                    return True
        except URLError, OSError, TimeoutError:
            time.sleep(0.4)
    return False


class ReportState:
    def __init__(self) -> None:
        self.event = threading.Event()
        self.payload: dict[str, Any] | None = None


def make_handler(state: ReportState) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args: object) -> None:
            return

        def do_OPTIONS(self) -> None:
            self.send_response(204)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "*")
            self.end_headers()

        def do_POST(self) -> None:
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length)
            try:
                state.payload = json.loads(raw.decode("utf-8"))
            except json.JSONDecodeError:
                state.payload = {
                    "ok": False,
                    "error": "invalid JSON report",
                    "raw": raw.decode("utf-8", "replace"),
                }
            self.send_response(204)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            state.event.set()

    return Handler


def print_manual_checklist() -> None:
    print("""
Memovi native packaged auth smoke (manual)
==========================================

This is not automated coverage. Evidence is the real WebView UI plus API
behavior, not TestClient or jsdom.

Prerequisites
  1. task docker-up
  2. task db:migrate
  3. task backend   (http://127.0.0.1:8000)
  4. A packaged binary from `pnpm --filter @memovi/desktop tauri:build`
     Do not use `task desktop` / `tauri dev` for this check: that origin is
     http://127.0.0.1:1420 (SameSite=Lax), which is a different cookie mode.

Steps and required evidence
  1. API is up
     Evidence: GET http://127.0.0.1:8000/ready succeeds.
  2. Launch the packaged/installed Memovi app (not tauri dev).
     Evidence: native window opens.
  3. Settings -> Diagnostics -> Client origin
     Evidence: origin is one of tauri://localhost, http://tauri.localhost,
     https://tauri.localhost. If you see http://127.0.0.1:1420, stop; that is
     development, not packaged.
  4. Register a unique user (or sign in).
     Evidence: the shell leaves the auth gate (home/workspace visible).
     HttpOnly cookies cannot be read from JS; success of the following /auth/me
     probe is the jar evidence.
  5. Authenticated session
     Evidence: product pages load; Diagnostics still reachable. That path
     called GET /auth/me with credentials from the WebView.
  6. Optional reload/relaunch
     Evidence: still signed in after reload (and after quit/relaunch if you
     choose). Session restore uses the same cookie jar.
  7. Sign out
     Evidence: auth gate returns.
  8. Unauthenticated
     Evidence: the app does not restore a session; retrying a protected
     action shows the sign-in screen.

Expected packaged origins (Tauri 2.11 in this repo, useHttpsScheme unset)
  Windows / Android: http://tauri.localhost
  Linux / macOS:     tauri://localhost

See docs/testing/NATIVE_DESKTOP_SMOKE.md.
""".strip())


def evaluate_report(payload: dict[str, Any]) -> int:
    origin = str(payload.get("origin") or "")
    print(json.dumps(payload, indent=2))
    if origin == DEV_DESKTOP_ORIGIN:
        print(
            "FAIL: origin is the Tauri dev server, not a packaged custom protocol. "
            "Build and launch the packaged binary.",
            file=sys.stderr,
        )
        return 1
    if origin not in PACKAGED_TAURI_ORIGINS:
        print(
            f"FAIL: origin {origin!r} is not in the packaged Tauri allowlist "
            f"{sorted(PACKAGED_TAURI_ORIGINS)}.",
            file=sys.stderr,
        )
        return 1
    raw_steps = payload.get("steps") or []
    steps = {str(item.get("name")): item for item in raw_steps if isinstance(item, dict)}
    me_authed = steps.get("me_after_register", {}).get("status")
    me_anon = steps.get("me_after_logout", {}).get("status")
    if me_authed != 200:
        print(
            "FAIL: packaged WebView did not authenticate GET /auth/me after register "
            "(cookie jar did not send the session).",
            file=sys.stderr,
        )
        return 1
    print("JAR PASS: packaged origin stored the session enough for GET /auth/me to return 200.")
    if me_anon != 401:
        print(
            "LOGOUT UNPROVEN: GET /auth/me was not 401 after POST /auth/logout "
            f"(got {me_anon!r}). Do not claim session clear from this run.",
            file=sys.stderr,
        )
        return 1
    print("LOGOUT PASS: GET /auth/me returned 401 after logout.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-base", default="http://127.0.0.1:8000")
    parser.add_argument("--binary", help="Path to memovi-desktop / Memovi binary")
    parser.add_argument("--timeout", type=float, default=90.0)
    parser.add_argument(
        "--allow-debug",
        action="store_true",
        help="Also search debug/ (tauri build --debug). Cargo check leftovers are not sufficient.",
    )
    parser.add_argument(
        "--manual",
        action="store_true",
        help="Print the manual checklist and optionally launch without the probe.",
    )
    parser.add_argument(
        "--launch-manual",
        action="store_true",
        help="With --manual, also launch the packaged binary (no JS probe).",
    )
    args = parser.parse_args(argv)

    if args.manual:
        print_manual_checklist()
        if not args.launch_manual:
            return 0
        binary = find_binary(args.binary, include_debug=args.allow_debug)
        if binary is None:
            print("No packaged desktop binary found. Build with pnpm tauri:build.", file=sys.stderr)
            return 2
        print(f"Launching {binary} without native-auth-smoke env.")
        subprocess.Popen([str(binary)])
        return 0

    if not api_ready(args.api_base, timeout_s=min(15.0, args.timeout)):
        print(
            f"API is not ready at {args.api_base}/ready. Start it with `task backend`.",
            file=sys.stderr,
        )
        return 2

    binary = find_binary(args.binary, include_debug=args.allow_debug)
    if binary is None:
        print(
            "No packaged desktop binary found. Build one first:\n"
            "  pnpm --filter @memovi/desktop tauri:build\n"
            "or a faster packaged debug build:\n"
            "  pnpm --filter @memovi/desktop exec tauri build --debug\n"
            "Then re-run `task desktop:smoke:native` (add --allow-debug for debug/).",
            file=sys.stderr,
        )
        return 2

    state = ReportState()
    server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(state))
    report_url = f"http://127.0.0.1:{server.server_address[1]}/report"
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    env = os.environ.copy()
    env["MEMOVI_NATIVE_AUTH_SMOKE"] = "1"
    env["MEMOVI_NATIVE_AUTH_SMOKE_API"] = args.api_base.rstrip("/")
    env["MEMOVI_NATIVE_AUTH_SMOKE_REPORT"] = report_url

    print(f"API ready. Launching packaged binary:\n  {binary}")
    print(f"Report listener: {report_url}")

    try:
        proc = subprocess.Popen([str(binary)], env=env)
    except OSError as exc:
        print(f"Failed to launch {binary}: {exc}", file=sys.stderr)
        server.shutdown()
        return 2

    finished = state.event.wait(timeout=args.timeout)
    proc.terminate()
    try:
        proc.wait(timeout=8)
    except subprocess.TimeoutExpired:
        proc.kill()
    server.shutdown()

    if not finished or state.payload is None:
        print(
            "FAIL: no report from the WebView before timeout. The packaged origin "
            "cookie jar is still unproven on this host.",
            file=sys.stderr,
        )
        return 1
    return evaluate_report(state.payload)


if __name__ == "__main__":
    raise SystemExit(main())
