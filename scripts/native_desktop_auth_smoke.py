"""Launch a packaged Memovi desktop binary and observe WebView session cookies.

This is not CI coverage. It requires a built Tauri binary, a display, and a
running API. It does not use WebDriver, Playwright, xvfb, or a bundled backend.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
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
CARGO_LOCK = Path("apps") / "desktop" / "src-tauri" / "Cargo.lock"


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def smoke_platform() -> str:
    system = sys.platform
    if system == "win32":
        return "windows"
    if system == "darwin":
        return "macos"
    if system.startswith("linux"):
        return "linux"
    return system


def host_os_label() -> str:
    kind = smoke_platform()
    if kind == "windows":
        return f"Windows {platform.version()}"
    if kind == "macos":
        version = platform.mac_ver()[0] or "unknown"
        return f"macOS {version}"
    if kind == "linux":
        release = _linux_os_release()
        if release:
            name = release.get("PRETTY_NAME") or release.get("NAME") or "Linux"
            version = release.get("VERSION_ID") or release.get("VERSION") or ""
            return f"{name} {version}".strip()
        return f"Linux {platform.release()}"
    return platform.platform()


def _linux_os_release() -> dict[str, str]:
    path = Path("/etc/os-release")
    if not path.is_file():
        return {}
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, raw = line.split("=", 1)
        values[key] = raw.strip().strip('"')
    return values


def tauri_version(repo_root: Path | None = None) -> str:
    lock = (repo_root or _repo_root()) / CARGO_LOCK
    if not lock.is_file():
        return "unknown"
    name_line = False
    for line in lock.read_text(encoding="utf-8", errors="replace").splitlines():
        if line == 'name = "tauri"':
            name_line = True
            continue
        if name_line and line.startswith("version = "):
            return line.split("=", 1)[1].strip().strip('"')
        name_line = False
    return "unknown"


def webkitgtk_version() -> str:
    if smoke_platform() != "linux":
        return ""
    for pkg in ("webkit2gtk-4.1", "webkit2gtk-4.0"):
        try:
            output = subprocess.check_output(
                ["pkg-config", "--modversion", pkg],
                text=True,
                timeout=2,
                stderr=subprocess.DEVNULL,
            )
        except OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired:
            continue
        version = output.strip()
        if version:
            return f"{pkg} {version}"
    return ""


def infer_webview(*, platform_name: str, user_agent: str = "") -> str:
    if platform_name == "windows":
        return "WebView2"
    if platform_name == "macos":
        return "WKWebView"
    if platform_name == "linux":
        gtk = webkitgtk_version()
        return gtk or "WebKitGTK"
    return user_agent or "unknown"


def has_display() -> bool:
    kind = smoke_platform()
    if kind == "linux":
        return bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))
    return True


def is_launchable(path: Path) -> bool:
    if path.is_file():
        return True
    macos_dir = path / "Contents" / "MacOS"
    return path.suffix == ".app" and macos_dir.is_dir()


def resolve_executable(artifact: Path) -> Path:
    if artifact.suffix == ".app" and artifact.is_dir():
        named = artifact / "Contents" / "MacOS" / "Memovi"
        if named.is_file():
            return named
        macos_dir = artifact / "Contents" / "MacOS"
        if macos_dir.is_dir():
            for child in sorted(macos_dir.iterdir()):
                if child.is_file():
                    return child
    return artifact


def _target_roots() -> list[Path]:
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
    return roots


def _binary_candidates(*, include_debug: bool) -> list[Path]:
    names = (
        "memovi-desktop.exe",
        "memovi-desktop",
        "Memovi.exe",
        "Memovi",
    )
    profiles = ("debug", "release") if include_debug else ("release",)
    candidates: list[Path] = []
    kind = smoke_platform()
    for root in _target_roots():
        for profile in profiles:
            profile_dir = root / profile
            if kind == "macos":
                macos_app = profile_dir / "bundle" / "macos" / "Memovi.app"
                candidates.append(macos_app)
                candidates.append(macos_app / "Contents" / "MacOS" / "Memovi")
            for name in names:
                candidates.append(profile_dir / name)
            if kind != "macos":
                macos_app = profile_dir / "bundle" / "macos" / "Memovi.app"
                candidates.append(macos_app / "Contents" / "MacOS" / "Memovi")
    if kind == "linux":
        candidates.extend(
            (
                Path("/usr/bin/memovi-desktop"),
                Path("/usr/bin/Memovi"),
                Path.home() / ".local" / "bin" / "memovi-desktop",
            )
        )
    return candidates


def find_binary(explicit: str | None, *, include_debug: bool = False) -> Path | None:
    if explicit:
        path = Path(explicit)
        return path if is_launchable(path) else None
    for candidate in _binary_candidates(include_debug=include_debug):
        if is_launchable(candidate):
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
  3. task backend   (http://127.0.0.1:8000) — already running; this smoke
     does not start FastAPI, Python, PostgreSQL, or MinIO
  4. A packaged binary from `pnpm --filter @memovi/desktop tauri:build`
     Windows: memovi-desktop.exe
     macOS:   unsigned Memovi.app (WKWebView; signing/notarization not required)
     Linux:   packaged memovi-desktop binary or installed .deb (WebKitGTK)
     Do not use `task desktop` / `tauri dev`: that origin is
     http://127.0.0.1:1420 (SameSite=Lax), a different cookie mode.

Steps and required evidence
  1. API is up
     Evidence: GET http://127.0.0.1:8000/ready succeeds.
  2. Launch the packaged/installed Memovi app (not tauri dev).
     Evidence: native window opens.
  3. Settings -> Diagnostics -> Client origin
     Evidence: origin is one of tauri://localhost, http://tauri.localhost,
     https://tauri.localhost. If you see http://127.0.0.1:1420, stop; that is
     development, not packaged. Record the origin the WebView actually reports.
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
     Evidence: GET /auth/me is 401; the app does not restore a session.

Expected packaged origins (Tauri 2.11 in this repo, useHttpsScheme unset)
  Windows / Android: http://tauri.localhost
  Linux / macOS:     tauri://localhost
  Record the live origin; do not assume one OS proves another.

See docs/testing/NATIVE_DESKTOP_SMOKE.md.
""".strip())


def step_map(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    raw_steps = payload.get("steps") or []
    return {str(item.get("name")): item for item in raw_steps if isinstance(item, dict)}


def lifecycle_codes(payload: dict[str, Any]) -> dict[str, Any]:
    steps = step_map(payload)
    return {
        "origin": str(payload.get("origin") or ""),
        "register": steps.get("register", {}).get("status"),
        "me_authenticated": steps.get("me_after_register", {}).get("status"),
        "logout": steps.get("logout", {}).get("status"),
        "me_after_logout": steps.get("me_after_logout", {}).get("status"),
        "me_repeat": steps.get("me_after_logout_repeat", {}).get("status"),
        "register_email": steps.get("register", {}).get("email"),
        "me_email": steps.get("me_after_register", {}).get("email"),
    }


def format_summary(
    *,
    platform_name: str,
    origin: str,
    api: str,
    register: object,
    me_authenticated: object,
    logout: object,
    me_after_logout: object,
    me_repeat: object,
    result: str,
    os_label: str = "",
    tauri: str = "",
    webview: str = "",
) -> str:
    lines = [f"platform={platform_name}"]
    if os_label:
        lines.append(f"os={os_label}")
    if tauri:
        lines.append(f"tauri={tauri}")
    if webview:
        lines.append(f"webview={webview}")
    lines.extend(
        (
            f"origin={origin or '(missing)'}",
            f"api={api}",
            f"register={register if register is not None else '(missing)'}",
            f"me_authenticated={me_authenticated if me_authenticated is not None else '(missing)'}",
            f"logout={logout if logout is not None else '(missing)'}",
            f"me_after_logout={me_after_logout if me_after_logout is not None else '(missing)'}",
            f"me_repeat={me_repeat if me_repeat is not None else '(missing)'}",
            f"result={result}",
        )
    )
    return "\n".join(lines)


def evaluate_report(
    payload: dict[str, Any],
    *,
    api_base: str,
    platform_name: str | None = None,
    os_label: str = "",
    tauri: str = "",
    webview: str = "",
) -> int:
    codes = lifecycle_codes(payload)
    origin = codes["origin"]
    kind = platform_name or str(payload.get("platform") or smoke_platform())
    resolved_webview = webview or infer_webview(
        platform_name=kind,
        user_agent=str(payload.get("userAgent") or ""),
    )
    result = "PASS"
    failures: list[str] = []

    if not origin:
        failures.append("origin cannot be determined")
    elif origin == DEV_DESKTOP_ORIGIN:
        failures.append(
            "origin is the Tauri dev server, not a packaged custom protocol. "
            "Build and launch the packaged binary."
        )
    elif origin not in PACKAGED_TAURI_ORIGINS:
        failures.append(
            f"origin {origin!r} is not in the packaged Tauri allowlist "
            f"{sorted(PACKAGED_TAURI_ORIGINS)}."
        )
    if codes["register"] != 201:
        failures.append(f"register expected 201, got {codes['register']!r}")
    if codes["me_authenticated"] != 200:
        failures.append(
            "packaged WebView did not authenticate GET /auth/me after register "
            f"(got {codes['me_authenticated']!r}; cookie jar did not send the session)."
        )
    register_email = codes["register_email"]
    me_email = codes["me_email"]
    if register_email and me_email and register_email != me_email:
        failures.append(
            "GET /auth/me email did not match the user registered in this run. "
            "A previous WebView profile session may have been used."
        )
    if codes["logout"] != 204:
        failures.append(f"logout expected 204, got {codes['logout']!r}")
    if codes["me_after_logout"] != 401:
        failures.append(
            "GET /auth/me was not 401 after POST /auth/logout "
            f"(got {codes['me_after_logout']!r}). Do not claim session clear from this run."
        )
    if codes["me_repeat"] != 401:
        failures.append(f"repeat GET /auth/me expected 401, got {codes['me_repeat']!r}")
    if payload.get("ok") is not True:
        failures.append(str(payload.get("error") or "probe reported ok=false"))

    if failures:
        result = "FAIL"
    summary = format_summary(
        platform_name=kind,
        origin=origin,
        api=api_base.rstrip("/"),
        register=codes["register"],
        me_authenticated=codes["me_authenticated"],
        logout=codes["logout"],
        me_after_logout=codes["me_after_logout"],
        me_repeat=codes["me_repeat"],
        result=result,
        os_label=os_label,
        tauri=tauri,
        webview=resolved_webview,
    )
    print(summary)
    print(json.dumps(payload, indent=2))
    if failures:
        for item in failures:
            print(f"FAIL: {item}", file=sys.stderr)
        return 1
    print("JAR PASS: packaged origin stored the session enough for GET /auth/me to return 200.")
    print("LOGOUT PASS: GET /auth/me returned 401 after logout (and on the repeat GET).")
    print("document.cookie is not proof: HttpOnly session cookies must stay invisible to JS.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-base", default="http://127.0.0.1:8000")
    parser.add_argument(
        "--binary",
        help="Path to memovi-desktop / Memovi / Memovi.app (packaged, not tauri dev)",
    )
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
    kind = smoke_platform()
    os_label = host_os_label()
    tauri = tauri_version()
    webview = infer_webview(platform_name=kind)

    if args.manual:
        print_manual_checklist()
        if not args.launch_manual:
            return 0
        binary = find_binary(args.binary, include_debug=args.allow_debug)
        if binary is None:
            print("No packaged desktop binary found. Build with pnpm tauri:build.", file=sys.stderr)
            return 2
        executable = resolve_executable(binary)
        print(f"Launching {executable} without native-auth-smoke env.")
        subprocess.Popen([str(executable)])
        return 0

    if not has_display():
        print(
            "No graphical display (DISPLAY/WAYLAND_DISPLAY unset). "
            "Native packaged smoke requires a real session. This project does not use xvfb.",
            file=sys.stderr,
        )
        return 2

    if not api_ready(args.api_base, timeout_s=min(15.0, args.timeout)):
        print(
            f"API is not ready at {args.api_base}/ready. Start it with `task backend`. "
            "This smoke does not start FastAPI, PostgreSQL, or MinIO.",
            file=sys.stderr,
        )
        return 2

    binary = find_binary(args.binary, include_debug=args.allow_debug)
    if binary is None:
        print(
            "No packaged desktop binary found. Build one first:\n"
            "  pnpm --filter @memovi/desktop tauri:build\n"
            "macOS: launch the unsigned Memovi.app from bundle/macos/\n"
            "Linux: launch target/release/memovi-desktop or the installed .deb binary\n"
            "or a faster packaged debug build:\n"
            "  pnpm --filter @memovi/desktop exec tauri build --debug\n"
            "Then re-run `task desktop:smoke:native` (add --allow-debug for debug/).",
            file=sys.stderr,
        )
        return 2

    executable = resolve_executable(binary)
    state = ReportState()
    server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(state))
    report_url = f"http://127.0.0.1:{server.server_address[1]}/report"
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    env = os.environ.copy()
    env["MEMOVI_NATIVE_AUTH_SMOKE"] = "1"
    env["MEMOVI_NATIVE_AUTH_SMOKE_API"] = args.api_base.rstrip("/")
    env["MEMOVI_NATIVE_AUTH_SMOKE_REPORT"] = report_url
    env["MEMOVI_NATIVE_AUTH_SMOKE_TAURI"] = tauri
    profile_dir = tempfile.mkdtemp(prefix="memovi-webview-smoke-")
    env["MEMOVI_NATIVE_AUTH_SMOKE_PROFILE"] = profile_dir

    print(f"platform={kind} os={os_label} tauri={tauri} webview={webview}")
    print(f"API ready. Launching packaged application:\n  {executable}")
    if executable != binary:
        print(f"Bundle: {binary}")
    print(f"Report listener: {report_url}")
    print(f"Temporary WebView profile: {profile_dir}")

    try:
        proc = subprocess.Popen([str(executable)], env=env)
    except OSError as exc:
        print(f"Failed to launch {executable}: {exc}", file=sys.stderr)
        server.shutdown()
        shutil.rmtree(profile_dir, ignore_errors=True)
        print(
            format_summary(
                platform_name=kind,
                origin="",
                api=args.api_base.rstrip("/"),
                register=None,
                me_authenticated=None,
                logout=None,
                me_after_logout=None,
                me_repeat=None,
                result="FAIL",
                os_label=os_label,
                tauri=tauri,
                webview=webview,
            )
        )
        return 2

    finished = state.event.wait(timeout=args.timeout)
    proc.terminate()
    try:
        proc.wait(timeout=8)
    except subprocess.TimeoutExpired:
        proc.kill()
    server.shutdown()
    shutil.rmtree(profile_dir, ignore_errors=True)

    if not finished or state.payload is None:
        print(
            format_summary(
                platform_name=kind,
                origin="",
                api=args.api_base.rstrip("/"),
                register=None,
                me_authenticated=None,
                logout=None,
                me_after_logout=None,
                me_repeat=None,
                result="FAIL",
                os_label=os_label,
                tauri=tauri,
                webview=webview,
            )
        )
        print(
            "FAIL: no report from the WebView before timeout. The packaged origin "
            "cookie jar is still unproven on this host.",
            file=sys.stderr,
        )
        return 1
    return evaluate_report(
        state.payload,
        api_base=args.api_base,
        platform_name=kind,
        os_label=os_label,
        tauri=tauri,
        webview=infer_webview(
            platform_name=kind,
            user_agent=str(state.payload.get("userAgent") or ""),
        ),
    )


if __name__ == "__main__":
    raise SystemExit(main())
