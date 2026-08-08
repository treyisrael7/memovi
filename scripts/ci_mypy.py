"""Run MyPy the same way Backend CI does, Windows-safe.

GitHub Actions historically passed every source file on the mypy argv. On
Windows that can exceed CreateProcess limits, so this script selects the same
files and invokes MyPy in-process via its Python API.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def _source_files() -> list[str]:
    listed = subprocess.check_output(
        ["git", "ls-files", "*.py", "*.pyi"],
        text=True,
    ).splitlines()
    return [
        path
        for path in listed
        if not Path(path).parts[0].startswith(".")
        and "tests" not in Path(path).parts
        and "scripts" not in Path(path).parts
    ]


def main() -> int:
    files = _source_files()
    if not files:
        print("No Python files found; skipping MyPy until backend code exists.")
        return 0

    print(f"MyPy checking {len(files)} source files")
    # Import after optional early exit so missing mypy fails clearly at call time.
    from mypy.api import run

    stdout, stderr, status = run(files)
    if stdout:
        sys.stdout.write(stdout)
    if stderr:
        sys.stderr.write(stderr)
    return status


if __name__ == "__main__":
    raise SystemExit(main())
