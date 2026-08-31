"""Helpers for tag-triggered desktop GitHub Releases.

Used by .github/workflows/release.yml. Does not change application version
files. Signing happens in the workflow via Tauri, not in this script.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import re
import shutil

TAURI_CONFIG = pathlib.Path("apps/desktop/src-tauri/tauri.conf.json")
ALLOWED_ARCH = {"x64", "arm64", "x86", "arm"}


def read_application_version() -> str:
    return json.loads(TAURI_CONFIG.read_text(encoding="utf-8"))["version"]


def runner_arch_label(raw: str) -> str:
    arch = raw.lower()
    if arch not in ALLOWED_ARCH:
        raise SystemExit(f"Unsupported runner.arch {raw!r}")
    return arch


def validate_tag(tag: str) -> dict[str, str]:
    if not re.fullmatch(r"v\d+\.\d+\.\d+", tag):
        raise SystemExit(f"Tag {tag!r} must match vMAJOR.MINOR.PATCH")
    version = read_application_version()
    expected = f"v{version}"
    if tag != expected:
        raise SystemExit(
            f"Tag {tag} does not match {TAURI_CONFIG} version {version} "
            f"(expected {expected}). Refusing to rewrite the application version."
        )
    prerelease = "true" if version.split(".", 1)[0] == "0" else "false"
    return {"version": version, "tag": tag, "prerelease": prerelease}


def _unique_file(directory: pathlib.Path, pattern: str) -> pathlib.Path:
    files = sorted(p for p in directory.glob(pattern) if p.is_file())
    if len(files) != 1:
        raise SystemExit(f"Expected exactly one {pattern} under {directory}, found {files}")
    return files[0]


def stage_linux(version: str, arch: str, dest_dir: pathlib.Path) -> pathlib.Path:
    src = _unique_file(
        pathlib.Path("apps/desktop/src-tauri/target/release/bundle/deb"),
        "*.deb",
    )
    dest = dest_dir / f"Memovi_{version}_linux_{arch}.deb"
    shutil.copy2(src, dest)
    return dest


def stage_windows(version: str, arch: str, dest_dir: pathlib.Path) -> list[pathlib.Path]:
    root = pathlib.Path("apps/desktop/src-tauri/target/release/bundle")
    nsis = _unique_file(root / "nsis", "*.exe")
    msi = _unique_file(root / "msi", "*.msi")
    exe_dest = dest_dir / f"Memovi_{version}_windows_{arch}_setup.exe"
    msi_dest = dest_dir / f"Memovi_{version}_windows_{arch}.msi"
    shutil.copy2(nsis, exe_dest)
    shutil.copy2(msi, msi_dest)
    return [exe_dest, msi_dest]


def stage_macos(version: str, arch: str, dest_dir: pathlib.Path) -> pathlib.Path:
    src = _unique_file(
        pathlib.Path("apps/desktop/src-tauri/target/release/bundle/dmg"),
        "*.dmg",
    )
    dest = dest_dir / f"Memovi_{version}_macos_{arch}.dmg"
    shutil.copy2(src, dest)
    return dest


def cmd_require_env(args: argparse.Namespace) -> None:
    missing = [name for name in args.names if not os.environ.get(name, "").strip()]
    if missing:
        raise SystemExit(
            "Missing required GitHub secrets for a signed release: "
            + ", ".join(missing)
            + ". Tag releases fail closed; they do not publish unsigned Windows/macOS packages."
        )
    print("Required signing secrets are present (values not printed).")


def cmd_validate(args: argparse.Namespace) -> None:
    result = validate_tag(args.tag)
    github_output = os.environ.get("GITHUB_OUTPUT")
    if github_output:
        with open(github_output, "a", encoding="utf-8") as fh:
            for key, value in result.items():
                fh.write(f"{key}={value}\n")
    print(
        f"Tag {result['tag']} matches application version {result['version']}; "
        f"prerelease={result['prerelease']}"
    )


def cmd_stage(args: argparse.Namespace) -> None:
    version = args.version or read_application_version()
    arch = runner_arch_label(args.arch)
    dest_dir = pathlib.Path(args.dest)
    dest_dir.mkdir(parents=True, exist_ok=True)
    if args.platform == "linux":
        staged = [stage_linux(version, arch, dest_dir)]
    elif args.platform == "windows":
        staged = stage_windows(version, arch, dest_dir)
    else:
        staged = [stage_macos(version, arch, dest_dir)]
    for path in staged:
        print(f"Staged {path}")


def _match_one(names: list[str], predicate, label: str) -> str:
    matched = [name for name in names if predicate(name)]
    if len(matched) != 1:
        raise SystemExit(f"Expected exactly one {label}, found {matched}")
    return matched[0]


def cmd_prepare(args: argparse.Namespace) -> None:
    version = args.version or read_application_version()
    tag = args.tag
    repo_url = args.repo_url.rstrip("/")
    assets_dir = pathlib.Path(args.assets_dir)
    files = {p.name: p for p in assets_dir.iterdir() if p.is_file() and p.name != "SHA256SUMS.txt"}
    names = list(files)

    linux = _match_one(
        names,
        lambda n: n.startswith(f"Memovi_{version}_linux_") and n.endswith(".deb"),
        "Linux .deb",
    )
    windows_exe = _match_one(
        names,
        lambda n: n.startswith(f"Memovi_{version}_windows_") and n.endswith("_setup.exe"),
        "Windows NSIS .exe",
    )
    windows_msi = _match_one(
        names,
        lambda n: (
            n.startswith(f"Memovi_{version}_windows_")
            and n.endswith(".msi")
            and not n.endswith("_setup.exe")
        ),
        "Windows MSI",
    )
    macos = _match_one(
        names,
        lambda n: n.startswith(f"Memovi_{version}_macos_") and n.endswith(".dmg"),
        "macOS .dmg",
    )

    packages = [files[n] for n in sorted([linux, windows_exe, windows_msi, macos])]
    extra = set(files) - {p.name for p in packages}
    if extra:
        raise SystemExit(f"Unexpected files in {assets_dir}: {sorted(extra)}")

    sums_path = assets_dir / "SHA256SUMS.txt"
    lines = []
    for path in packages:
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        lines.append(f"{digest}  {path.name}")
    sums_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    blob = f"{repo_url}/blob/{tag}"
    notes = "\n".join(
        [
            f"# Memovi {version}",
            "",
            f"Desktop packages from tag `{tag}`.",
            "",
            "## V1 package formats",
            "",
            f"- Linux: `{linux}` — **unsigned**",
            f"- Windows NSIS: `{windows_exe}` — Authenticode-signed",
            f"- Windows MSI: `{windows_msi}` — Authenticode-signed",
            f"- macOS: `{macos}` — Developer ID signed and notarized (`.app` inside the DMG)",
            "- Checksums: `SHA256SUMS.txt` (SHA-256 of these final assets, not signatures)",
            "",
            "## Signing",
            "",
            "Windows installers are Authenticode-signed. macOS ships a Developer ID",
            "Application-signed `.app` inside the `.dmg`, notarized with App Store Connect.",
            "Linux `.deb` remains unsigned. There is no auto-updater.",
            "PR/main Desktop CI packaging stays unsigned and is not this Release.",
            "",
            "## External backend required",
            "",
            "The packaged Tauri application is a desktop client only. It does **not**",
            "bundle FastAPI, Python, PostgreSQL, or MinIO. Run the Memovi API and",
            "local infrastructure separately before launching the app.",
            "",
            f"Setup: [`README.md`]({blob}/README.md) and",
            f"[`apps/desktop/README.md`]({blob}/apps/desktop/README.md).",
            "Packaging vs native verification:",
            f"[`docs/testing/DESKTOP_TESTING.md`]({blob}/docs/testing/DESKTOP_TESTING.md).",
            "",
            "Package creation is not native window launch or WebView authentication proof.",
            "",
        ]
    )
    pathlib.Path(args.notes_file).write_text(notes + "\n", encoding="utf-8")
    print("Release assets:")
    print("\n".join(lines))


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    require_env = sub.add_parser(
        "require-env",
        help="Fail if named environment variables (GitHub secrets) are empty",
    )
    require_env.add_argument("names", nargs="+")
    require_env.set_defaults(func=cmd_require_env)

    validate = sub.add_parser("validate", help="Check tag matches tauri.conf.json version")
    validate.add_argument("--tag", required=True)
    validate.set_defaults(func=cmd_validate)

    stage = sub.add_parser("stage", help="Copy the V1 package to a versioned filename")
    stage.add_argument("--platform", required=True, choices=("linux", "windows", "macos"))
    stage.add_argument("--arch", required=True, help="GitHub runner.arch (e.g. X64, ARM64)")
    stage.add_argument("--version", default="")
    stage.add_argument("--dest", default="release-assets")
    stage.set_defaults(func=cmd_stage)

    prepare = sub.add_parser("prepare", help="Verify assets, write SHA256SUMS.txt and notes")
    prepare.add_argument("--assets-dir", default="release-assets")
    prepare.add_argument("--notes-file", default="release-notes.md")
    prepare.add_argument("--tag", required=True)
    prepare.add_argument("--version", default="")
    prepare.add_argument("--repo-url", required=True)
    prepare.set_defaults(func=cmd_prepare)

    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
