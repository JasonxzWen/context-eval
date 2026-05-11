import subprocess
from pathlib import Path

import pytest

from context_eval.config import (
    ConfigError,
    filter_tasks,
    load_config,
    load_tasks,
    validate_config_files,
)
from context_eval.models import TaskConfig, TaskFile


def _run_git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        capture_output=True,
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
    assert config.agent.telemetry.collector == "none"


def test_yaml_config_and_tasks_parse_validation_timeout_defaults(tmp_path: Path) -> None:
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
      timeout_seconds: 15
      commands:
        - "python -m pytest tests/test_bug.py"
""",
        encoding="utf-8",
    )
    config_path = tmp_path / "context-eval.yaml"
    config_path.write_text(
        """
repo:
  path: "./repo"
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
evaluation:
  timeout_seconds: 45
  commands:
    - "python -m pytest"
""",
        encoding="utf-8",
    )

    config = load_config(config_path)
    tasks = load_tasks(tasks_path)

    assert config.evaluation.timeout_seconds == 45
    assert tasks.tasks[0].validation.timeout_seconds == 15


def test_validation_timeout_seconds_must_be_positive(tmp_path: Path) -> None:
    config_path = _write_config_fixture(tmp_path)
    config_path.write_text(
        config_path.read_text(encoding="utf-8")
        + """
evaluation:
  timeout_seconds: 0
""",
        encoding="utf-8",
    )

    with pytest.raises(ConfigError, match="timeout_seconds"):
        load_config(config_path)


def test_yaml_config_parses_optional_json_file_telemetry(tmp_path: Path) -> None:
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
""",
        encoding="utf-8",
    )
    config_path = tmp_path / "context-eval.yaml"
    config_path.write_text(
        """
repo:
  path: "./repo"
agent:
  name: "test-agent"
  command: "agent --telemetry {telemetry_file}"
  telemetry:
    collector: "json-file"
    file: "metrics/usage.json"
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

    assert config.agent.telemetry.collector == "json-file"
    assert config.agent.telemetry.file == "metrics/usage.json"


def test_yaml_config_resolves_prompt_template_relative_to_config(tmp_path: Path) -> None:
    config_path = _write_config_fixture(tmp_path)
    prompt_template = tmp_path / "prompts" / "agent-task.md"
    prompt_template.parent.mkdir()
    prompt_template.write_text("Task={task_id}", encoding="utf-8")
    config_path.write_text(
        config_path.read_text(encoding="utf-8").replace(
            'command: "agent -p {prompt_file}"',
            'command: "agent -p {prompt_file}"\n  prompt_template: "./prompts/agent-task.md"',
        ),
        encoding="utf-8",
    )

    config = load_config(config_path)

    assert config.agent.prompt_template == prompt_template.resolve()


def test_validate_config_rejects_missing_prompt_template(tmp_path: Path) -> None:
    config_path = _write_config_fixture(tmp_path)
    config_path.write_text(
        config_path.read_text(encoding="utf-8").replace(
            'command: "agent -p {prompt_file}"',
            'command: "agent -p {prompt_file}"\n  prompt_template: "./missing-prompt.md"',
        ),
        encoding="utf-8",
    )

    with pytest.raises(ConfigError, match="agent.prompt_template does not exist"):
        validate_config_files(config_path)


def test_config_schema_error_names_file_and_field(tmp_path: Path) -> None:
    config_path = _write_config_fixture(tmp_path)
    config_path.write_text(
        config_path.read_text(encoding="utf-8").replace('  path: "./repo"\n', ""),
        encoding="utf-8",
    )

    with pytest.raises(ConfigError) as excinfo:
        load_config(config_path)

    message = str(excinfo.value)
    assert "context-eval.yaml: repo.path" in message
    assert "Field required" in message


def test_config_overlay_target_error_names_variant_and_overlay_field(tmp_path: Path) -> None:
    config_path = _write_config_fixture(tmp_path)
    config_path.write_text(
        config_path.read_text(encoding="utf-8").replace(
            'target: "AGENTS.md"',
            'target: "../escape.md"',
        ),
        encoding="utf-8",
    )

    with pytest.raises(ConfigError) as excinfo:
        load_config(config_path)

    message = str(excinfo.value)
    assert "context-eval.yaml: variants.baseline.overlays[0].target" in message
    assert "overlay target must be a safe relative path" in message


def test_task_schema_error_names_task_id_and_field(tmp_path: Path) -> None:
    config_path = _write_config_fixture(tmp_path)
    (tmp_path / "tasks.yaml").write_text(
        """
tasks:
  - id: "task-1"
    prompt: "Fix the bug."
    validation:
      timeout_seconds: 0
""",
        encoding="utf-8",
    )

    with pytest.raises(ConfigError) as excinfo:
        validate_config_files(config_path)

    message = str(excinfo.value)
    assert "tasks.yaml: tasks[task-1].validation.timeout_seconds" in message
    assert "greater than or equal to 1" in message


def test_duplicate_task_id_error_names_task_file_and_task_id(tmp_path: Path) -> None:
    config_path = _write_config_fixture(tmp_path)
    (tmp_path / "tasks.yaml").write_text(
        """
tasks:
  - id: "task-1"
    prompt: "Fix the first bug."
  - id: "task-1"
    prompt: "Fix the second bug."
""",
        encoding="utf-8",
    )

    with pytest.raises(ConfigError) as excinfo:
        validate_config_files(config_path)

    message = str(excinfo.value)
    assert "tasks.yaml: tasks[task-1].id" in message
    assert "duplicate task id" in message


def test_yaml_config_rejects_unsafe_telemetry_file(tmp_path: Path) -> None:
    config_path = _write_config_fixture(tmp_path)
    text = config_path.read_text(encoding="utf-8")
    config_path.write_text(
        text.replace(
            'command: "agent -p {prompt_file}"',
            (
                'command: "agent --telemetry {telemetry_file}"\n'
                "  telemetry:\n"
                '    collector: "json-file"\n'
                '    file: "../usage.json"'
            ),
        ),
        encoding="utf-8",
    )

    with pytest.raises(ConfigError, match="telemetry file must be a safe relative path"):
        load_config(config_path)


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


def test_filter_tasks_combines_dimensions_without_mutating_task_file() -> None:
    task_file = TaskFile(
        tasks=[
            TaskConfig(
                id="docs-easy",
                prompt="Fix docs.",
                category="documentation",
                difficulty="easy",
            ),
            TaskConfig(
                id="docs-hard",
                prompt="Rewrite docs.",
                category="documentation",
                difficulty="hard",
            ),
            TaskConfig(
                id="runtime-easy",
                prompt="Fix runtime.",
                category="runtime",
                difficulty="easy",
            ),
        ]
    )

    filtered = filter_tasks(
        task_file,
        task_ids=[],
        categories=["documentation"],
        difficulties=["easy", "medium"],
    )

    assert [task.id for task in filtered.tasks] == ["docs-easy"]
    assert [task.id for task in task_file.tasks] == [
        "docs-easy",
        "docs-hard",
        "runtime-easy",
    ]


def test_filter_tasks_rejects_unknown_task_ids() -> None:
    task_file = TaskFile(tasks=[TaskConfig(id="known", prompt="Fix docs.")])

    with pytest.raises(ConfigError, match="unknown task id"):
        filter_tasks(
            task_file,
            task_ids=["known", "missing"],
            categories=[],
            difficulties=[],
        )


def test_filter_tasks_rejects_empty_selection() -> None:
    task_file = TaskFile(tasks=[TaskConfig(id="known", prompt="Fix docs.", category="docs")])

    with pytest.raises(ConfigError, match="task filters selected no tasks"):
        filter_tasks(
            task_file,
            task_ids=[],
            categories=["runtime"],
            difficulties=[],
        )
