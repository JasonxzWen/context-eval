"""Check for hidden local state that can invalidate release readiness."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


BLOCKED_DIRS = (
    ".context-eval",
    "build",
    "dist",
)
BLOCKED_FILES = (
    ".codex/config.toml",
)


def _display(path: Path, *, is_dir: bool | None = None) -> str:
    text = path.as_posix()
    directory = path.is_dir() if is_dir is None else is_dir
    return f"{text}/" if directory and not text.endswith("/") else text


def check_release_state(root: Path) -> list[str]:
    errors: list[str] = []
    root = root.resolve()

    if not root.is_dir():
        return [f"{root}: not a directory"]

    for relative in BLOCKED_DIRS:
        path = root / relative
        if path.exists():
            errors.append(f"hidden local release blocker: {relative}/")

    for path in sorted(root.glob("*.egg-info")):
        errors.append(
            f"hidden local release blocker: "
            f"{_display(path.relative_to(root), is_dir=path.is_dir())}"
        )

    for relative in BLOCKED_FILES:
        path = root / relative
        if path.exists():
            errors.append(f"hidden local release blocker: {Path(relative).as_posix()}")

    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "root",
        nargs="?",
        default=Path.cwd(),
        type=Path,
        help="Repository root to inspect. Defaults to the current directory.",
    )
    args = parser.parse_args(argv)

    errors = check_release_state(args.root)
    if errors:
        for error in errors:
            print(f"error: {error}", file=sys.stderr)
        return 1

    print(f"Release state check passed: {args.root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
