"""Prepare release artifacts without tagging or publishing."""

from __future__ import annotations

import argparse
import importlib.util
import shutil
import subprocess
import sys
from pathlib import Path


def _load_release_state_checker():
    path = Path(__file__).resolve().parent / "check-release-state.py"
    spec = importlib.util.spec_from_file_location("check_release_state", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load release-state checker: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.check_release_state


check_release_state = _load_release_state_checker()


def check_changelog(root: Path) -> list[str]:
    path = root / "CHANGELOG.md"
    if not path.exists():
        return ["CHANGELOG.md is required before release preparation"]

    text = path.read_text(encoding="utf-8")
    if "## Unreleased" not in text:
        return ["CHANGELOG.md must contain ## Unreleased"]

    after_unreleased = text.split("## Unreleased", maxsplit=1)[1]
    unreleased = after_unreleased
    next_heading = unreleased.find("\n## ")
    if next_heading != -1:
        unreleased = unreleased[:next_heading]
    if not any(line.lstrip().startswith("- ") for line in unreleased.splitlines()):
        released = after_unreleased[next_heading:] if next_heading != -1 else ""
        if not any(line.lstrip().startswith("- ") for line in released.splitlines()):
            return ["CHANGELOG.md must contain at least one unreleased or released bullet"]

    return []


def check_dist_dir(dist_dir: Path) -> list[str]:
    if not dist_dir.exists():
        return []
    if not dist_dir.is_dir():
        return [f"dist directory must be a directory: {dist_dir}"]
    if any(dist_dir.iterdir()):
        return [f"dist directory must be empty before release build: {dist_dir}"]
    return []


def _display_command(command: list[str]) -> str:
    display = ["python" if item == sys.executable else item for item in command]
    script_dir = Path(__file__).resolve().parent
    repo_root = script_dir.parent
    normalized = []
    for item in display:
        try:
            path = Path(item).resolve()
        except OSError:
            normalized.append(item)
            continue
        if path == script_dir / "inspect-package-artifacts.py":
            normalized.append("scripts/inspect-package-artifacts.py")
        elif path == script_dir / "install-smoke-artifacts.py":
            normalized.append("scripts/install-smoke-artifacts.py")
        elif path == repo_root:
            normalized.append(".")
        else:
            normalized.append(item)
    return " ".join(normalized)


def _run(command: list[str], *, cwd: Path, dry_run: bool) -> int:
    if dry_run:
        print(f"DRY RUN: would run {_display_command(command)}")
        return 0
    print(f"Running: {_display_command(command)}")
    return subprocess.run(command, cwd=cwd, check=False).returncode


def prepare_release(root: Path, dist_dir: Path, *, dry_run: bool) -> int:
    root = root.resolve()
    dist_dir = dist_dir.resolve()

    errors = []
    errors.extend(check_changelog(root))
    errors.extend(check_release_state(root))
    errors.extend(check_dist_dir(dist_dir))

    if errors:
        for error in errors:
            print(f"error: {error}", file=sys.stderr)
        return 1

    print("CHANGELOG.md check passed")
    print(f"Release state check passed: {root}")
    print(f"Release artifact directory ready: {dist_dir}")

    if not dry_run:
        dist_dir.mkdir(parents=True, exist_ok=True)

    script_dir = Path(__file__).resolve().parent
    inspector = script_dir / "inspect-package-artifacts.py"
    install_smoke = script_dir / "install-smoke-artifacts.py"
    commands = [
        [sys.executable, "-m", "build", "--outdir", str(dist_dir)],
        [sys.executable, str(inspector), str(dist_dir)],
        [
            sys.executable,
            str(install_smoke),
            "--root",
            str(root),
            "--dist-dir",
            str(dist_dir),
        ],
    ]

    for command in commands:
        exit_code = _run(command, cwd=root, dry_run=dry_run)
        if exit_code != 0:
            return exit_code

    print("Manual publish checkpoint: create tags and upload packages outside this script.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        default=Path.cwd(),
        type=Path,
        help="Repository root to prepare. Defaults to the current directory.",
    )
    parser.add_argument(
        "--dist-dir",
        required=True,
        type=Path,
        help="Empty artifact output directory for wheel and sdist files.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate inputs and print build/inspection commands without running them.",
    )
    args = parser.parse_args(argv)

    if shutil.which("git") is None:
        print("warning: git executable not found; continuing without Git command checks")

    return prepare_release(args.root, args.dist_dir, dry_run=args.dry_run)


if __name__ == "__main__":
    raise SystemExit(main())
