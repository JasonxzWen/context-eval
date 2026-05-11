"""Validate package artifact contents for release readiness."""

from __future__ import annotations

import argparse
import sys
import tarfile
import zipfile
from pathlib import Path


REQUIRED_PREFIXES = (
    "context_eval/",
    "context_eval/reports/templates/",
)

FORBIDDEN_PREFIXES = (
    ".context-eval/",
    ".agents/",
    ".codex/skills/",
    "openspec/",
    "scripts/",
)


def _normalized_name(name: str) -> str:
    normalized = name.replace("\\", "/")
    while normalized.startswith("./"):
        normalized = normalized[2:]
    normalized = normalized.lstrip("/")
    parts = normalized.split("/", maxsplit=1)
    if len(parts) == 2 and parts[0].startswith("context_eval-"):
        return parts[1]
    return normalized


def _archive_names(path: Path) -> set[str]:
    if path.suffix == ".whl":
        with zipfile.ZipFile(path) as archive:
            return {_normalized_name(name) for name in archive.namelist()}

    if path.name.endswith(".tar.gz"):
        with tarfile.open(path, "r:gz") as archive:
            return {_normalized_name(member.name) for member in archive.getmembers()}

    raise ValueError(f"Unsupported artifact type: {path}")


def _contains_prefix(names: set[str], prefix: str) -> bool:
    return any(name == prefix.rstrip("/") or name.startswith(prefix) for name in names)


def _inspect_artifact(path: Path) -> list[str]:
    names = _archive_names(path)
    errors: list[str] = []

    for prefix in REQUIRED_PREFIXES:
        if not _contains_prefix(names, prefix):
            errors.append(f"{path.name}: missing required entry {prefix}")

    for prefix in FORBIDDEN_PREFIXES:
        matches = sorted(name for name in names if name == prefix.rstrip("/") or name.startswith(prefix))
        for match in matches:
            errors.append(f"{path.name}: forbidden entry {match} from {prefix}")

    return errors


def inspect_dist(dist_dir: Path) -> list[str]:
    errors: list[str] = []
    if not dist_dir.is_dir():
        return [f"{dist_dir}: not a directory"]

    wheels = sorted(dist_dir.glob("*.whl"))
    sdists = sorted(dist_dir.glob("*.tar.gz"))

    if not wheels:
        errors.append(f"{dist_dir}: missing wheel artifact")
    if not sdists:
        errors.append(f"{dist_dir}: missing sdist artifact")

    for artifact in [*wheels, *sdists]:
        errors.extend(_inspect_artifact(artifact))

    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dist_dir", type=Path, help="Directory containing built wheel and sdist artifacts.")
    args = parser.parse_args(argv)

    errors = inspect_dist(args.dist_dir)
    if errors:
        for error in errors:
            print(f"error: {error}", file=sys.stderr)
        return 1

    print(f"Package artifact inspection passed: {args.dist_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
