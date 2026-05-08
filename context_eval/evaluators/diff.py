from __future__ import annotations

from pathlib import Path

from context_eval.logging import run_command
from context_eval.models import DiffStats


def parse_numstat(output: str) -> DiffStats:
    changed_files = 0
    insertions = 0
    deletions = 0
    touched_paths: list[str] = []

    for raw_line in output.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        parts = line.split("\t")
        if len(parts) < 3:
            continue
        added, removed, path = parts[0], parts[1], "\t".join(parts[2:])
        changed_files += 1
        if added != "-":
            insertions += int(added)
        if removed != "-":
            deletions += int(removed)
        touched_paths.append(path)

    return DiffStats(
        changed_files=changed_files,
        insertions=insertions,
        deletions=deletions,
        touched_paths=touched_paths,
    )


def create_diff_baseline(workspace: Path, index_file: Path) -> str:
    index_file.parent.mkdir(parents=True, exist_ok=True)
    env = {"GIT_INDEX_FILE": str(index_file)}
    read_tree = run_command(["git", "read-tree", "HEAD"], cwd=workspace, shell=False, env=env)
    if read_tree.exit_code != 0:
        raise RuntimeError(read_tree.stderr.strip() or "git read-tree failed")

    add = run_command(["git", "add", "-A"], cwd=workspace, shell=False, env=env)
    if add.exit_code != 0:
        raise RuntimeError(add.stderr.strip() or "git add baseline failed")

    tree = run_command(["git", "write-tree"], cwd=workspace, shell=False, env=env)
    if tree.exit_code != 0:
        raise RuntimeError(tree.stderr.strip() or "git write-tree failed")
    return tree.stdout.strip()


def collect_git_diff(
    workspace: Path,
    patch_path: Path,
    baseline_tree: str | None = None,
    index_file: Path | None = None,
) -> DiffStats:
    patch_path.parent.mkdir(parents=True, exist_ok=True)
    env = {"GIT_INDEX_FILE": str(index_file)} if baseline_tree and index_file else None
    if baseline_tree:
        run_command(["git", "add", "--intent-to-add", "."], cwd=workspace, shell=False, env=env)
        patch_args = ["git", "diff", "--no-ext-diff", baseline_tree, "--"]
        numstat_args = ["git", "diff", "--numstat", baseline_tree, "--"]
    else:
        patch_args = ["git", "diff", "--no-ext-diff"]
        numstat_args = ["git", "diff", "--numstat"]

    patch = run_command(patch_args, cwd=workspace, shell=False, env=env)
    patch_path.write_text(patch.stdout, encoding="utf-8")

    numstat = run_command(numstat_args, cwd=workspace, shell=False, env=env)
    return parse_numstat(numstat.stdout)
