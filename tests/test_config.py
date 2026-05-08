from pathlib import Path

from context_eval.config import load_config, load_tasks, validate_config_files


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
