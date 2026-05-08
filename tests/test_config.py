import subprocess
from pathlib import Path

import pytest

from context_eval.config import ConfigError
from context_eval.config import load_config, load_tasks, validate_config_files


def _run_git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def test_yaml_config_and_tasks_parse(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    context_dir = tmp_path / "contexts" / "baseline"
    context_dir.mkdir(parents=True)
    (context_dir / "AGENTS.md").write_text("# Instructions\n", encoding="utf-8")
    tasks_path = tmp_path / "tasks.yaml"
    tasks_path.write_text(
        """
tasks:
  - id: "task-1"
    prompt: "Fix the bug."
    validation:
      commands:
        - "python -m pytest"
""",
        encoding="utf-8",
    )
    config_path = tmp_path / "context-eval.yaml"
    config_path.write_text(
        """
repo:
  path: "./repo"
  base_ref: "main"
agent:
  name: "test-agent"
  command: "agent -p {prompt_file}"
tasks: "./tasks.yaml"
variants:
  baseline:
    description: "Baseline"
    overlays:
      - source: "./contexts/baseline/AGENTS.md"
        target: "AGENTS.md"
""",
        encoding="utf-8",
    )

    config = load_config(config_path)
    tasks = load_tasks(tasks_path)
    validated_config, validated_tasks = validate_config_files(config_path)

    assert config.repo.path == repo.resolve()
    assert config.tasks == tasks_path.resolve()
    assert config.variants["baseline"].overlays[0].source == (context_dir / "AGENTS.md").resolve()
    assert tasks.tasks[0].id == "task-1"
    assert tasks.tasks[0].validation.commands == ["python -m pytest"]
    assert validated_config.agent.name == "test-agent"
    assert validated_tasks.tasks[0].prompt == "Fix the bug."


def _write_config_fixture(
    tmp_path: Path,
    *,
    repo_path: str = "./repo",
    base_ref: str = "HEAD",
    task_repo_ref: str | None = None,
) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir(exist_ok=True)
    context_dir = tmp_path / "contexts" / "baseline"
    context_dir.mkdir(parents=True, exist_ok=True)
    (context_dir / "AGENTS.md").write_text("# Instructions\n", encoding="utf-8")
    task_repo_ref_line = f'\n    repo_ref: "{task_repo_ref}"' if task_repo_ref else ""
    (tmp_path / "tasks.yaml").write_text(
        f"""
tasks:
  - id: "task-1"{task_repo_ref_line}
    prompt: "Fix the bug."
""",
        encoding="utf-8",
    )
    config_path = tmp_path / "context-eval.yaml"
    config_path.write_text(
        f"""
repo:
  path: "{repo_path}"
  base_ref: "{base_ref}"
agent:
  name: "test-agent"
  command: "agent -p {{prompt_file}}"
tasks: "./tasks.yaml"
variants:
  baseline:
    description: "Baseline"
    overlays:
      - source: "./contexts/baseline/AGENTS.md"
        target: "AGENTS.md"
""",
        encoding="utf-8",
    )
    return config_path


def test_default_validation_does_not_require_git_repository(tmp_path: Path) -> None:
    config_path = _write_config_fixture(tmp_path)

    config, tasks = validate_config_files(config_path)

    assert config.repo.path == (tmp_path / "repo").resolve()
    assert tasks.tasks[0].id == "task-1"


def test_strict_validation_requires_git_repository(tmp_path: Path) -> None:
    config_path = _write_config_fixture(tmp_path)

    with pytest.raises(ConfigError, match="repo.path is not a Git repository"):
        validate_config_files(config_path, strict=True)


def test_strict_validation_requires_base_ref_to_resolve(tmp_path: Path) -> None:
    config_path = _write_config_fixture(tmp_path, base_ref="missing-ref")
    repo = tmp_path / "repo"
    _run_git(repo, "init")

    with pytest.raises(ConfigError, match="repo.base_ref does not resolve"):
        validate_config_files(config_path, strict=True)


def test_strict_validation_requires_task_repo_refs_to_resolve(tmp_path: Path) -> None:
    config_path = _write_config_fixture(tmp_path, task_repo_ref="missing-task-ref")
    repo = tmp_path / "repo"
    _run_git(repo, "init")
    (repo / "README.md").write_text("base\n", encoding="utf-8")
    _run_git(repo, "add", "README.md")
    _run_git(
        repo,
        "-c",
        "user.email=test@example.com",
        "-c",
        "user.name=Test",
        "commit",
        "-m",
        "init",
    )

    with pytest.raises(ConfigError, match="task 'task-1' repo_ref does not resolve"):
        validate_config_files(config_path, strict=True)
