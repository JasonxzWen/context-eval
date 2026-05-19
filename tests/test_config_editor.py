from __future__ import annotations

import shutil
from pathlib import Path

import pytest
import yaml

from context_eval.config import validate_config_files
from context_eval.config_editor import (
    build_editable_model,
    export_editable_yaml,
    validate_editable_model,
)


def test_editable_model_includes_supported_fields_from_basic_example() -> None:
    config, tasks = validate_config_files(Path("examples/basic/context-eval.yaml"))

    model = build_editable_model(config, tasks)

    assert model.repo.path == "../fixture-repo"
    assert model.repo.base_ref == "main"
    assert model.agent.name == "example-agent"
    assert model.agent.command == 'python scripts/example_agent.py "{prompt_file}"'
    assert model.agent.timeout_minutes == 5
    assert model.agent.network == "disabled"
    assert model.tasks_path == "./tasks.yaml"
    assert model.evaluation_timeout_seconds is None
    assert model.evaluation_commands == ["python -m pytest"]
    assert [variant.name for variant in model.variants] == ["baseline", "experiment"]
    assert model.variants[0].description == "Original AGENTS.md"
    assert model.variants[0].overlays[0].source == "./contexts/baseline/AGENTS.md"
    assert model.variants[0].overlays[0].target == "AGENTS.md"
    assert model.variants[1].overlays[1].source == "./contexts/experiment/docs"
    assert model.variants[1].overlays[1].target == "docs/deepwiki"
    assert len(model.tasks) == 1
    task = model.tasks[0]
    assert task.id == "fix-greeting-punctuation"
    assert task.title == "Fix greeting punctuation"
    assert task.prompt.startswith("Fix the fixture greeting")
    assert task.category == "runtime"
    assert task.difficulty == "easy"
    assert task.validation_timeout_seconds is None
    assert task.validation_commands == []


def test_editable_model_exports_separate_yaml_that_validates_round_trip(tmp_path: Path) -> None:
    copied_examples = tmp_path / "examples"
    shutil.copytree(Path("examples/basic"), copied_examples / "basic")
    shutil.copytree(Path("examples/fixture-repo"), copied_examples / "fixture-repo")
    config_path = copied_examples / "basic" / "context-eval.yaml"
    tasks_path = copied_examples / "basic" / "tasks.yaml"
    config, tasks = validate_config_files(config_path)
    model = build_editable_model(config, tasks)

    exported = export_editable_yaml(model)
    config_data = yaml.safe_load(exported.config_yaml)
    task_data = yaml.safe_load(exported.tasks_yaml)

    assert config_data["tasks"] == "./tasks.yaml"
    assert "repo" in config_data
    assert "agent" in config_data
    assert "variants" in config_data
    assert "evaluation" in config_data
    assert "Fix the fixture greeting" not in exported.config_yaml
    assert list(task_data) == ["tasks"]
    assert "repo" not in task_data
    assert "agent" not in task_data
    assert task_data["tasks"][0]["prompt"].startswith("Fix the fixture greeting")

    config_path.write_text(exported.config_yaml, encoding="utf-8")
    tasks_path.write_text(exported.tasks_yaml, encoding="utf-8")
    round_tripped_config, round_tripped_tasks = validate_config_files(config_path)

    assert round_tripped_config.repo.path == (copied_examples / "fixture-repo").resolve()
    assert round_tripped_config.agent.timeout_minutes == 5
    assert round_tripped_config.evaluation.commands == ["python -m pytest"]
    assert set(round_tripped_config.variants) == {"baseline", "experiment"}
    assert round_tripped_tasks.tasks[0].prompt == tasks.tasks[0].prompt
    assert round_tripped_tasks.tasks[0].title == tasks.tasks[0].title


def test_editable_model_exports_task_validation_commands(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    context_dir = tmp_path / "contexts" / "baseline"
    context_dir.mkdir(parents=True)
    (context_dir / "AGENTS.md").write_text("# Instructions\n", encoding="utf-8")
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
evaluation:
  commands:
    - "python -m pytest"
""",
        encoding="utf-8",
    )
    tasks_path = tmp_path / "tasks.yaml"
    tasks_path.write_text(
        """
tasks:
  - id: "task-1"
    prompt: |
      Fix the bug.
      Keep the patch small.
    repo_ref: "main"
    validation:
      commands:
        - "python -m pytest tests/test_bug.py"
""",
        encoding="utf-8",
    )
    config, tasks = validate_config_files(config_path)
    model = build_editable_model(config, tasks)

    exported = export_editable_yaml(model)
    task_data = yaml.safe_load(exported.tasks_yaml)

    assert model.tasks[0].validation_commands == ["python -m pytest tests/test_bug.py"]
    assert task_data["tasks"][0]["validation"]["commands"] == [
        "python -m pytest tests/test_bug.py"
    ]


def test_editable_model_preserves_agents_map_on_export(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    context_dir = tmp_path / "contexts" / "baseline"
    context_dir.mkdir(parents=True)
    (context_dir / "AGENTS.md").write_text("# Instructions\n", encoding="utf-8")
    config_path = tmp_path / "context-eval.yaml"
    config_path.write_text(
        """
repo:
  path: "./repo"
agents:
  codex:
    kind: "codex-cli"
    command: "codex exec - < {prompt_file}"
  coco:
    kind: "coco"
    command: "coco -p {prompt_file}"
  trae:
    kind: "traecli"
    command: "traecli -p \\"{prompt}\\""
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
    tasks_path = tmp_path / "tasks.yaml"
    tasks_path.write_text(
        """
tasks:
  - id: "task-1"
    prompt: "Fix the bug."
""",
        encoding="utf-8",
    )
    config, tasks = validate_config_files(config_path)
    model = build_editable_model(config, tasks)

    exported = export_editable_yaml(model)
    config_data = yaml.safe_load(exported.config_yaml)

    assert model.agent_shape == "agents"
    assert [agent.name for agent in model.agents] == ["codex", "coco", "trae"]
    assert "agent" not in config_data
    assert config_data["agents"]["codex"]["kind"] == "codex-cli"
    assert config_data["agents"]["coco"]["kind"] == "coco"
    assert config_data["agents"]["coco"]["command"] == "coco -p {prompt_file}"
    assert config_data["agents"]["trae"]["kind"] == "traecli"
    assert config_data["agents"]["trae"]["command"] == 'traecli -p "{prompt}"'

    config_path.write_text(exported.config_yaml, encoding="utf-8")
    round_tripped_config, _ = validate_config_files(config_path)
    assert list(round_tripped_config.agent_profiles()) == ["codex", "coco", "trae"]


def test_editable_model_round_trips_hybrid_task_fields_and_unknowns(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    context_dir = tmp_path / "contexts" / "baseline"
    context_dir.mkdir(parents=True)
    (context_dir / "AGENTS.md").write_text("# Instructions\n", encoding="utf-8")
    config_path = tmp_path / "context-eval.yaml"
    config_path.write_text(
        """
repo:
  path: "./repo"
agents:
  coco:
    kind: "coco"
    command: "coco -p {prompt_file}"
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
    tasks_path = tmp_path / "tasks.yaml"
    tasks_path.write_text(
        """
tasks:
  - id: "task-1"
    prompt: "Fix the bug."
    expected_outcome:
      summary: "README contains fixed."
      acceptance_points:
        - "Fixed marker is present."
    hard_evaluation:
      enabled: true
      required_paths:
        - "README.md"
      command_checks:
        - label: "readme-marker"
          command: "python -c \\"print('fixed')\\""
          expected: "fixed"
    soft_evaluation:
      enabled: true
      mode: "payload-only"
      rubric:
        - name: "quality"
          weight: 1
          description: "Patch is clear."
    x_task_unknown:
      keep: true
""",
        encoding="utf-8",
    )
    config, tasks = validate_config_files(config_path)
    model = build_editable_model(config, tasks)

    exported = export_editable_yaml(model)
    task_data = yaml.safe_load(exported.tasks_yaml)

    task = model.tasks[0]
    assert task.expected_outcome is not None
    assert task.expected_outcome.summary == "README contains fixed."
    assert task.hard_evaluation is not None
    assert task.hard_evaluation.required_paths == ["README.md"]
    assert task.hard_evaluation.command_checks[0].label == "readme-marker"
    assert task.soft_evaluation is not None
    assert task.soft_evaluation.rubric[0].name == "quality"
    assert task.extra_fields == {"x_task_unknown": {"keep": True}}
    assert task_data["tasks"][0]["expected_outcome"]["summary"] == "README contains fixed."
    assert task_data["tasks"][0]["hard_evaluation"]["required_paths"] == ["README.md"]
    assert task_data["tasks"][0]["hard_evaluation"]["command_checks"] == [
        {
            "label": "readme-marker",
            "command": "python -c \"print('fixed')\"",
            "expected": "fixed",
            "timeout_seconds": 60,
        }
    ]
    assert task_data["tasks"][0]["soft_evaluation"]["mode"] == "payload-only"
    assert task_data["tasks"][0]["x_task_unknown"] == {"keep": True}


def test_editable_model_exports_validation_timeout_defaults(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    context_dir = tmp_path / "contexts" / "baseline"
    context_dir.mkdir(parents=True)
    (context_dir / "AGENTS.md").write_text("# Instructions\n", encoding="utf-8")
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
    config, tasks = validate_config_files(config_path)
    model = build_editable_model(config, tasks)

    exported = export_editable_yaml(model)
    config_data = yaml.safe_load(exported.config_yaml)
    task_data = yaml.safe_load(exported.tasks_yaml)

    assert model.evaluation_timeout_seconds == 45
    assert model.tasks[0].validation_timeout_seconds == 15
    assert config_data["evaluation"]["timeout_seconds"] == 45
    assert task_data["tasks"][0]["validation"]["timeout_seconds"] == 15


def test_editable_yaml_export_rejects_duplicate_variant_names() -> None:
    config, tasks = validate_config_files(Path("examples/basic/context-eval.yaml"))
    model = build_editable_model(config, tasks)
    model.variants.append(model.variants[0].model_copy())

    try:
        export_editable_yaml(model)
    except ValueError as exc:
        assert "duplicate variant names: baseline" in str(exc)
    else:
        raise AssertionError("expected duplicate variant names to fail")


def test_editable_yaml_export_rejects_duplicate_task_ids() -> None:
    config, tasks = validate_config_files(Path("examples/basic/context-eval.yaml"))
    model = build_editable_model(config, tasks)
    model.tasks.append(model.tasks[0].model_copy())

    try:
        export_editable_yaml(model)
    except ValueError as exc:
        assert "duplicate task ids: fix-greeting-punctuation" in str(exc)
    else:
        raise AssertionError("expected duplicate task ids to fail")


def test_validate_editable_model_reports_persistence_blockers() -> None:
    config, tasks = validate_config_files(Path("examples/basic/context-eval.yaml"))
    model = build_editable_model(config, tasks)
    model.repo.path = " "
    model.agent.timeout_minutes = 0
    model.agent.network = "maybe"
    model.variants[0].overlays[0].target = "../AGENTS.md"
    model.tasks[0].prompt = ""
    model.tasks[0].validation_commands = [" "]

    issues = validate_editable_model(model)

    assert issues == [
        "repo.path is required",
        "agent.timeout_minutes must be a positive integer",
        "agent.network must be disabled or enabled",
        "variant 1 overlay 1 target must be a safe relative path",
        "task 1 prompt is required",
        "task 1 validation command 1 is required",
    ]


def test_editable_yaml_export_blocks_invalid_model_before_persistence() -> None:
    config, tasks = validate_config_files(Path("examples/basic/context-eval.yaml"))
    model = build_editable_model(config, tasks)
    model.repo.base_ref = ""

    with pytest.raises(ValueError, match="export blocked"):
        export_editable_yaml(model)
