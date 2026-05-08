from __future__ import annotations

import re
import shutil
from pathlib import Path

from context_eval.logging import run_command


class WorkspaceError(RuntimeError):
    """Raised when a repository workspace cannot be prepared."""


def slugify(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9_.-]+", "-", value).strip("-")
    return slug or "case"


def create_workspace(
    repo_path: Path,
    repo_ref: str,
    run_dir: Path,
    task_id: str,
    variant: str,
    case_id: str | None = None,
) -> Path:
    workspace_name = slugify(case_id) if case_id else f"{slugify(task_id)}__{slugify(variant)}"
    workspace = run_dir / "workspaces" / workspace_name
    workspace.parent.mkdir(parents=True, exist_ok=True)
    if workspace.exists():
        shutil.rmtree(workspace)

    result = run_command(
        ["git", "-C", str(repo_path), "worktree", "add", "--detach", str(workspace), repo_ref],
        cwd=repo_path,
        shell=False,
    )
    if result.exit_code != 0:
        raise WorkspaceError(
            result.stderr.strip() or result.stdout.strip() or "git worktree add failed"
        )
    return workspace


def remove_workspace(repo_path: Path, workspace: Path) -> None:
    if not workspace.exists():
        return
    result = run_command(
        ["git", "-C", str(repo_path), "worktree", "remove", "--force", str(workspace)],
        cwd=repo_path,
        shell=False,
    )
    if result.exit_code != 0 and workspace.exists():
        shutil.rmtree(workspace)
