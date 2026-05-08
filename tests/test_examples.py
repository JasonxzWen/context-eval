import shutil
import subprocess
import sys
from pathlib import Path

from context_eval.config import validate_config_files


def _run(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=cwd,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def test_basic_example_targets_fixture_repo() -> None:
    config, task_file = validate_config_files(Path("examples/basic/context-eval.yaml"))

    assert config.repo.path == Path("examples/fixture-repo").resolve()
    assert config.repo.base_ref == "main"
    assert task_file.tasks[0].id == "fix-greeting-punctuation"


def test_fixture_repo_setup_initializes_local_git_history(tmp_path: Path) -> None:
    source = Path("examples/fixture-repo")
    fixture = tmp_path / "fixture-repo"
    shutil.copytree(source, fixture)

    _run([sys.executable, "setup_fixture_repo.py"], cwd=fixture)

    head = _run(["git", "rev-parse", "--verify", "main^{commit}"], cwd=fixture)
    assert head.stdout.strip()
