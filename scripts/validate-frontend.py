"""Run the frontend validation gate from the repository root."""

from __future__ import annotations

import argparse
import os
import platform
import subprocess
import sys
from pathlib import Path

INSTALL_COMMAND_LABEL = "npm ci"
BROWSER_INSTALL_COMMAND_LABEL = "npx playwright install"
VALIDATE_COMMAND_LABEL = "npm run validate"


def _command(name: str) -> str:
    if os.name == "nt":
        return f"{name}.cmd"
    return name


def _run(args: list[str], cwd: Path) -> None:
    print(f"+ {' '.join(args)}")
    subprocess.run(args, cwd=cwd, check=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Install optional frontend dependencies and run npm run validate."
    )
    parser.add_argument(
        "--install",
        action="store_true",
        help="Run npm ci in frontend/ before validation.",
    )
    parser.add_argument(
        "--install-browsers",
        action="store_true",
        help="Install the Chromium browser required by Playwright.",
    )
    parser.add_argument(
        "--install-system-deps",
        action="store_true",
        help="On Linux, ask Playwright to install system dependencies too.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = Path(__file__).resolve().parents[1]
    frontend_dir = repo_root / "frontend"

    if not (frontend_dir / "package.json").exists():
        print("frontend/package.json was not found", file=sys.stderr)
        return 1

    npm = _command("npm")
    npx = _command("npx")
    os.environ.setdefault("CONTEXT_EVAL_PYTHON", sys.executable)

    if args.install:
        _run([npm, "ci"], cwd=frontend_dir)

    if args.install_browsers:
        browser_args = [npx, "playwright", "install"]
        if args.install_system_deps and platform.system() == "Linux":
            browser_args.append("--with-deps")
        browser_args.append("chromium")
        _run(browser_args, cwd=frontend_dir)

    _run([npm, "run", "validate"], cwd=frontend_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
