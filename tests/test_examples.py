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
        capture_output=True,
        text=True,
    )


def test_basic_example_targets_fixture_repo() -> None:
    config, task_file = validate_config_files(Path("examples/basic/context-eval.yaml"))

    assert config.repo.path == Path("examples/fixture-repo").resolve()
    assert config.repo.base_ref == "main"
    assert task_file.tasks[0].id == "fix-greeting-punctuation"


def test_agent_matrix_example_validates_profiles_and_cli_filter() -> None:
    config, task_file = validate_config_files(Path("examples/agent-matrix/context-eval.yaml"))

    assert config.repo.path == Path("examples/fixture-repo").resolve()
    assert list(config.agents) == ["codex", "claude", "trae", "coco"]
    assert config.agents["trae"].kind == "traecli"
    assert config.agents["trae"].command == 'traecli -p "{prompt}"'
    assert task_file.tasks[0].id == "fix-greeting-punctuation"

    result = _run(
        [
            sys.executable,
            "-m",
            "context_eval",
            "run",
            "--config",
            "examples/agent-matrix/context-eval.yaml",
            "--dry-run",
            "--agent",
            "trae",
            "--variant",
            "experiment",
        ],
        cwd=Path("."),
    )

    assert "Agents: trae" in result.stdout
    assert 'trae (traecli): traecli -p "{prompt}"' in result.stdout
    assert "agent=trae task=fix-greeting-punctuation variant=experiment" in result.stdout
    assert "agent=codex" not in result.stdout


def test_coco_visual_example_validates_hybrid_task_shape() -> None:
    config, task_file = validate_config_files(Path("examples/coco-visual/context-eval.yaml"))

    assert list(config.agents) == ["coco"]
    assert config.agents["coco"].kind == "coco"
    assert (
        config.agents["coco"].command
        == 'coco -y --query-timeout 10m --bash-tool-timeout 5m -p "{prompt}"'
    )
    task = task_file.tasks[0]
    assert task.expected_outcome.summary
    assert task.hard_evaluation.enabled is True
    assert task.soft_evaluation.mode == "payload-only"
    assert task.hard_evaluation.required_paths == ["fixture_app/greetings.py"]


def test_fixture_repo_setup_initializes_local_git_history(tmp_path: Path) -> None:
    source = Path("examples/fixture-repo")
    fixture = tmp_path / "fixture-repo"
    shutil.copytree(source, fixture)

    _run([sys.executable, "setup_fixture_repo.py"], cwd=fixture)

    head = _run(["git", "rev-parse", "--verify", "main^{commit}"], cwd=fixture)
    assert head.stdout.strip()
