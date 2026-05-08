from __future__ import annotations

import shutil
from pathlib import Path

from context_eval.models import OverlayConfig


class OverlayError(RuntimeError):
    """Raised when a context overlay cannot be applied."""


def _ensure_inside_workspace(path: Path, workspace: Path) -> None:
    try:
        path.resolve().relative_to(workspace.resolve())
    except ValueError as exc:
        raise OverlayError(f"overlay target escapes workspace: {path}") from exc


def apply_overlay(workspace: Path, overlay: OverlayConfig) -> None:
    source = overlay.source
    target = workspace / overlay.target
    _ensure_inside_workspace(target, workspace)

    if not source.exists():
        raise OverlayError(f"overlay source does not exist: {source}")

    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() or target.is_symlink():
        if target.is_dir() and not target.is_symlink():
            shutil.rmtree(target)
        else:
            target.unlink()

    if source.is_dir():
        shutil.copytree(source, target)
    else:
        shutil.copy2(source, target)


def apply_overlays(workspace: Path, overlays: list[OverlayConfig]) -> None:
    for overlay in overlays:
        apply_overlay(workspace, overlay)
